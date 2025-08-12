#!/bin/bash

# Simple test script for LangExtract API
# Tests extraction from a 30-minute sales meeting transcript

echo "🧪 Testing LangExtract API with Sales Meeting"
echo "============================================="

# Check API key
if [ -z "$LANGEXTRACT_API_KEY" ]; then
    echo "❌ Set your API key: export LANGEXTRACT_API_KEY='your_key'"
    exit 1
fi

echo "✅ API Key: ${LANGEXTRACT_API_KEY:0:10}..."
echo ""

# Run /visualize endpoint (does extraction + generates artifacts)
echo "🚀 Calling /visualize endpoint..."
RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/visualize \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $LANGEXTRACT_API_KEY" \
  -d @test_sales_meeting.json)

echo "📄 Response:"
echo "$RESPONSE" | jq .

# Show generated files
HTML_PATH=$(echo "$RESPONSE" | jq -r '.html // empty')
if [ -n "$HTML_PATH" ] && [ "$HTML_PATH" != "null" ]; then
    echo ""
    echo "📁 Generated Files:"
    echo "   HTML Report: $HTML_PATH"
    echo "   JSONL: $(echo "$RESPONSE" | jq -r '.jsonl // empty')"
    echo "   Run Dir: $(echo "$RESPONSE" | jq -r '.run_dir // empty')"
fi

echo ""
echo "✅ Test completed!"
