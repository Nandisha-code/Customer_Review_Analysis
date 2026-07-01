from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from ml_service import SERVICE


def _json_default(value):
    if hasattr(value, 'item'):
        return value.item()
    return str(value)


class ApiHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status_code: int = 200, content_type: str = 'application/json') -> None:
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._set_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed_url = urlparse(self.path)

        if parsed_url.path == '/health':
            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}, default=_json_default).encode('utf-8'))
            return

        if parsed_url.path == '/api/products':
            params = parse_qs(parsed_url.query)
            query = params.get('query', [''])[0]
            products = SERVICE.search_products(query)
            payload = {'products': products}
            self._set_headers()
            self.wfile.write(json.dumps(payload, default=_json_default).encode('utf-8'))
            return

        if parsed_url.path == '/api/product-feedback':
            params = parse_qs(parsed_url.query)
            product = params.get('product', [''])[0]
            try:
                payload = SERVICE.summarize_product(product)
                self._set_headers()
                self.wfile.write(json.dumps(payload, default=_json_default).encode('utf-8'))
            except ValueError as error:
                self._set_headers(400)
                self.wfile.write(json.dumps({'error': str(error)}, default=_json_default).encode('utf-8'))
            return

        self._set_headers(404)
        self.wfile.write(json.dumps({'error': 'Not found'}, default=_json_default).encode('utf-8'))


def main() -> None:
    host = os.getenv('BACKEND_HOST', '127.0.0.1')
    port = int(os.getenv('BACKEND_PORT', '8000'))
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f'Backend running at http://{host}:{port}')
    server.serve_forever()


if __name__ == '__main__':
    main()
