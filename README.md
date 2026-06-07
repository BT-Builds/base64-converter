# Base64 Converter API

Encode and decode Base64 strings via HTTP API.

## Endpoints

### POST /encode
Encode text to Base64.
```json
{"text": "Hello World", "encoding": "utf-8"}
```
**Response:** `{"original": "Hello World", "encoded": "SGVsbG8gV29ybGQ=", "encoding": "utf-8"}`

### POST /decode
Decode Base64 to text.
```json
{"base64_string": "SGVsbG8gV29ybGQ=", "encoding": "utf-8"}
```
**Response:** `{"original": "SGVsbG8gV29ybGQ=", "decoded": "Hello World", "encoding": "utf-8"}`

### POST /validate
Validate if a string is valid Base64.
```json
{"base64_string": "SGVsbG8gV29ybGQ="}
```
**Response:** `{"valid": true, "message": "Valid Base64 string"}`

### POST /info
Get metadata about a Base64 string without decoding.
```json
{"base64_string": "SGVsbG8gV29ybGQ="}
```
**Response:** `{"length": 16, "padding_chars": 1, "alphanumeric_ratio": 1.0, "decoded_length": 11, "valid": true}`

### GET /health
Health check endpoint (no auth required).

## cURL Examples

```bash
# Encode
curl -X POST https://base64-converter.vercel.app/encode \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello World"}'

# Decode
curl -X POST https://base64-converter.vercel.app/decode \
  -H "Content-Type: application/json" \
  -d '{"base64_string": "SGVsbG8gV29ybGQ="}'

# Validate
curl -X POST https://base64-converter.vercel.app/validate \
  -H "Content-Type: application/json" \
  -d '{"base64_string": "SGVsbG8gV29ybGQ="}'
```

## Postman
[![Run in Postman](https://run.pstmn.io/button.svg)](https://raw.githubusercontent.com/BT-Builds/base64-converter/main/postman_collection.json)
