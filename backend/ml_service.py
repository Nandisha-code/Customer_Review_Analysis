from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC


DATA_PATH = Path(__file__).resolve().parent / 'data' / 'customer_reviews.csv'


@dataclass(slots=True)
class ProductFeedbackService:
    cleaned_df: pd.DataFrame
    results_df: pd.DataFrame
    best_model_name: str
    best_model: Pipeline

    @classmethod
    def build(cls) -> 'ProductFeedbackService':
        cleaned_df = _load_and_clean_data(DATA_PATH)
        results_df, best_model_name, best_model = _train_best_model(cleaned_df)
        return cls(
            cleaned_df=cleaned_df,
            results_df=results_df,
            best_model_name=best_model_name,
            best_model=best_model,
        )

    @property
    def product_names(self) -> list[str]:
        return sorted(
            self.cleaned_df['product_name']
            .dropna()
            .astype(str)
            .unique()
            .tolist(),
            key=str.lower,
        )

    def search_products(self, query: str) -> list[str]:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return self.product_names

        exact_matches = [
            product
            for product in self.product_names
            if product.lower() == normalized_query
        ]
        if exact_matches:
            return exact_matches

        contains_matches = [
            product
            for product in self.product_names
            if normalized_query in product.lower()
        ]
        return contains_matches

    def summarize_product(self, query: str) -> dict[str, Any]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError('Product name is required.')

        matched_df = self._match_product_rows(normalized_query)
        if matched_df.empty:
            return {
                'query': normalized_query,
                'matched': False,
                'message': 'No matching product was found.',
                'suggestions': self.search_products(normalized_query)[:8],
            }

        predictions = self.best_model.predict(matched_df['review_text'])
        sentiment_series = pd.Series(predictions, index=matched_df.index)
        positive_mask = sentiment_series == 'Positive'

        if hasattr(self.best_model.named_steps['model'], 'predict_proba'):
            probabilities = self.best_model.predict_proba(matched_df['review_text'])
            positive_class_index = list(self.best_model.classes_).index('Positive')
            positive_probabilities = probabilities[:, positive_class_index]
        else:
            decision_scores = self.best_model.decision_function(matched_df['review_text'])
            positive_probabilities = pd.Series(decision_scores).rank(pct=True).to_numpy()

        top_reviews = (
            matched_df.assign(
                predicted_sentiment=predictions,
                confidence=(positive_probabilities * 100).round(2),
            )
            .sort_values(['helpful_votes', 'rating'], ascending=False)
            .head(5)
            .loc[:, [
                'review_text',
                'rating',
                'predicted_sentiment',
                'confidence',
                'reviewer_age',
                'helpful_votes',
            ]]
            .to_dict(orient='records')
        )

        average_rating = round(float(matched_df['rating'].mean()), 2)
        positive_percent = round(float(positive_mask.mean() * 100), 2)
        negative_percent = round(100 - positive_percent, 2)
        average_confidence = round(float(pd.Series(positive_probabilities).mean() * 100), 2)

        return {
            'query': normalized_query,
            'matched': True,
            'matched_products': sorted(matched_df['product_name'].astype(str).unique().tolist()),
            'product_name': sorted(matched_df['product_name'].astype(str).unique().tolist())[0],
            'category_breakdown': (
                matched_df.groupby('category', as_index=False)
                .size()
                .sort_values('size', ascending=False)
                .to_dict(orient='records')
            ),
            'review_count': int(len(matched_df)),
            'average_rating': average_rating,
            'positive_percent': positive_percent,
            'negative_percent': negative_percent,
            'average_confidence': average_confidence,
            'best_model': self.best_model_name,
            'model_comparison': self.results_df.round(4).to_dict(orient='records'),
            'top_reviews': top_reviews,
        }

    def _match_product_rows(self, query: str) -> pd.DataFrame:
        normalized_query = query.strip().lower()
        exact_matches = self.cleaned_df[
            self.cleaned_df['product_name'].astype(str).str.lower() == normalized_query
        ]
        if not exact_matches.empty:
            return exact_matches.copy()

        contains_matches = self.cleaned_df[
            self.cleaned_df['product_name'].astype(str).str.contains(normalized_query, case=False, na=False)
        ]
        return contains_matches.copy()


def _load_and_clean_data(data_path: Path) -> pd.DataFrame:
    raw_lines = pd.read_csv(data_path, header=None, dtype=str).fillna('').astype(str).values.tolist()
    records: list[dict[str, Any]] = []

    for row in raw_lines[1:]:
        parts = [part.strip() for part in row]
        id_product = parts[0] or parts[1]
        if not id_product:
            continue

        id_parts = id_product.split(' ', 1)
        if len(id_parts) != 2:
            continue

        review_id, product_name = id_parts
        rating_match = re.match(r'^(\d+)\s*(.*)$', parts[4])
        if not rating_match:
            continue

        rating = int(rating_match.group(1))
        review_text = rating_match.group(2).strip()
        fragment = parts[5]
        if fragment and not fragment.isdigit() and fragment.lower() not in {'positive', 'negative'}:
            review_text = f'{review_text}{fragment}'

        review_text = re.sub(r'\s+(positive|negative)\s*$', '', review_text, flags=re.IGNORECASE).strip()
        numeric_values = [int(part) for part in parts if part.isdigit()]
        if len(numeric_values) < 2:
            continue

        true_sentiment = 'Negative' if any('negative' in part.lower() for part in parts) else 'Positive'

        records.append(
            {
                'review_id': int(review_id),
                'product_name': product_name,
                'category': parts[2] or pd.NA,
                'rating': rating,
                'review_text': review_text,
                'true_sentiment': true_sentiment,
                'reviewer_age': numeric_values[-2],
                'helpful_votes': numeric_values[-1],
            }
        )

    return pd.DataFrame(records).drop_duplicates().reset_index(drop=True)


def _train_best_model(cleaned_df: pd.DataFrame) -> tuple[pd.DataFrame, str, Pipeline]:
    model_df = cleaned_df[['review_text', 'true_sentiment']].dropna().copy()
    X = model_df['review_text']
    y = model_df['true_sentiment']

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    candidates = {
        'Logistic Regression': LogisticRegression(max_iter=1000),
        'Naive Bayes': MultinomialNB(),
        'SVM': LinearSVC(),
        'Random Forest': RandomForestClassifier(n_estimators=200, random_state=42),
    }

    evaluations: list[dict[str, Any]] = []
    trained_models: dict[str, Pipeline] = {}

    for name, estimator in candidates.items():
        pipeline = Pipeline(
            [
                ('tfidf', TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=5000)),
                ('model', estimator),
            ]
        )
        pipeline.fit(X_train, y_train)
        predictions = pipeline.predict(X_test)
        evaluations.append(
            {
                'Model': name,
                'Accuracy': accuracy_score(y_test, predictions),
                'F1 Score': f1_score(y_test, predictions, average='weighted'),
            }
        )
        trained_models[name] = pipeline

    results_df = pd.DataFrame(evaluations).sort_values(['F1 Score', 'Accuracy'], ascending=False).reset_index(drop=True)
    best_model_name = str(results_df.iloc[0]['Model'])
    return results_df, best_model_name, trained_models[best_model_name]


SERVICE = ProductFeedbackService.build()
