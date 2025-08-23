#!/bin/bash

# Mobile Dialer API Test Commands
# Make sure your API server is running on http://localhost:8000

API_KEY="ef19241d-40c1-4711-adc6-682130932d4d"
DEV_API_KEY="711ddbd9-292a-4212-9850-40fa17ce7405"
BASE_URL="http://localhost:8000"
TEST_NUMBER="19025809678"
CALLER_ID="15551234567"

echo "🚀 Mobile Dialer API Test Commands"
echo "=================================="
echo "API Key: $API_KEY"
echo "Dev Key: $DEV_API_KEY"
echo "Test Number: $TEST_NUMBER"
echo "Base URL: $BASE_URL"
echo ""

# Function to run command with description
run_test() {
    echo "📋 $1"
    echo "Command: $2"
    echo "Response:"
    eval $2
    echo ""
    echo "---"
    echo ""
}

# 1. Health Check
run_test "Health Check" \
"curl -s '$BASE_URL/health' | jq"

# 2. Check Connection (no mock)
run_test "Check Connection - No Mock (should be false)" \
"curl -s -H 'X-API-Key: $API_KEY' '$BASE_URL/check-connection?dialed_number=$TEST_NUMBER&caller_id=$CALLER_ID' | jq"

# 3. Add Mock Number
run_test "Add Mock Number" \
"curl -s -X POST -H 'Content-Type: application/json' -H 'X-API-Key: $DEV_API_KEY' -d '{\"numbers\": [\"$TEST_NUMBER\"]}' '$BASE_URL/mock-connect' | jq"

# 4. Check Connection (with mock)
run_test "Check Connection - With Mock (should be true)" \
"curl -s -H 'X-API-Key: $API_KEY' '$BASE_URL/check-connection?dialed_number=$TEST_NUMBER&caller_id=$CALLER_ID' | jq"

# 5. Mock Status
run_test "Check Mock Status" \
"curl -s -H 'X-API-Key: $DEV_API_KEY' '$BASE_URL/mock-status' | jq"

# 6. Add Range of Mock Numbers
run_test "Add Mock Number Range" \
"curl -s -X POST -H 'Content-Type: application/json' -H 'X-API-Key: $DEV_API_KEY' -d '{\"numbers\": [\"555-0100:555-0105\"]}' '$BASE_URL/mock-connect' | jq"

# 7. Test Range Number
run_test "Test Range Number (5550102)" \
"curl -s -H 'X-API-Key: $API_KEY' '$BASE_URL/check-connection?dialed_number=5550102' | jq"

# 8. Clear Mocks
run_test "Clear All Mocks" \
"curl -s -X DELETE -H 'X-API-Key: $DEV_API_KEY' '$BASE_URL/clear-mocks' | jq"

# 9. Test Invalid API Key
run_test "Test Invalid API Key (should fail)" \
"curl -s -H 'X-API-Key: invalid-key' '$BASE_URL/check-connection?dialed_number=$TEST_NUMBER' | jq"

# 10. Test Missing API Key
run_test "Test Missing API Key (should fail)" \
"curl -s '$BASE_URL/check-connection?dialed_number=$TEST_NUMBER' | jq"

echo "✅ All tests completed!"
echo ""
echo "💡 Tips:"
echo "- Make sure your API server is running: python main.py"
echo "- Or with Docker: docker-compose up -d"
echo "- Check logs if any tests fail"
echo "- Update BASE_URL for production testing"

