#!/bin/bash
# Mortgage Protection Leads Pipeline
# Pulls Monmouth County home sales from Propwire, skip traces via Tracerfy
# Delivers ready-to-dial CSV

set -e

# Config
TRACERFY_API_KEY="${TRACERFY_API_KEY:-}"
OUTPUT_DIR="/home/clawd/clawd/leads"
DATE=$(date +%Y-%m-%d)
OUTPUT_FILE="${OUTPUT_DIR}/monmouth_leads_${DATE}.csv"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

echo "[$(date)] Starting mortgage leads pipeline..."

# Step 1: Get property data from Propwire (or use cached nj.com data for now)
# Note: Propwire requires manual export or scraper - using nj.com scraped data as backup
PROPERTY_DATA="/home/clawd/clawd/monmouth_mortgage_leads_jan2026.csv"

if [ ! -f "$PROPERTY_DATA" ]; then
    echo "ERROR: No property data found at $PROPERTY_DATA"
    exit 1
fi

echo "[$(date)] Using property data from: $PROPERTY_DATA"

# Step 2: Convert property data to Tracerfy format
# Tracerfy needs: address, city, state, first_name, last_name
TRACERFY_INPUT="/tmp/tracerfy_input_${DATE}.csv"

echo "address,city,state,first_name,last_name,mail_address,mail_city,mail_state" > "$TRACERFY_INPUT"

# For now, we need owner names from Propwire. Using placeholder until Propwire integration
# This will be updated once we have Propwire data with owner names
tail -n +2 "$PROPERTY_DATA" | while IFS=, read -r address town price sqft beds baths ppsf score; do
    # Clean the address (remove quotes)
    addr=$(echo "$address" | tr -d '"')
    # Town is already clean
    echo "${addr},${town},NJ,OWNER,LOOKUP,${addr},${town},NJ"
done >> "$TRACERFY_INPUT"

RECORD_COUNT=$(tail -n +2 "$TRACERFY_INPUT" | wc -l)
echo "[$(date)] Prepared $RECORD_COUNT records for skip tracing"

# Step 3: Submit to Tracerfy API
if [ -z "$TRACERFY_API_KEY" ]; then
    echo "ERROR: TRACERFY_API_KEY not set"
    exit 1
fi

echo "[$(date)] Submitting to Tracerfy API..."

RESPONSE=$(curl -s -X POST "https://tracerfy.com/v1/api/trace/" \
    -H "Authorization: Bearer $TRACERFY_API_KEY" \
    -F "csv_file=@$TRACERFY_INPUT" \
    -F "address_column=address" \
    -F "city_column=city" \
    -F "state_column=state" \
    -F "first_name_column=first_name" \
    -F "last_name_column=last_name" \
    -F "mail_address_column=mail_address" \
    -F "mail_city_column=mail_city" \
    -F "mail_state_column=mail_state")

QUEUE_ID=$(echo "$RESPONSE" | jq -r '.queue_id')

if [ "$QUEUE_ID" = "null" ] || [ -z "$QUEUE_ID" ]; then
    echo "ERROR: Failed to create queue. Response: $RESPONSE"
    exit 1
fi

echo "[$(date)] Queue created: $QUEUE_ID"

# Step 4: Poll for completion
echo "[$(date)] Waiting for skip trace to complete..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    sleep 20
    
    STATUS=$(curl -s -X GET "https://tracerfy.com/v1/api/queues/" \
        -H "Authorization: Bearer $TRACERFY_API_KEY" \
        -H "Content-Type: application/json")
    
    PENDING=$(echo "$STATUS" | jq -r ".[] | select(.id == $QUEUE_ID) | .pending")
    DOWNLOAD_URL=$(echo "$STATUS" | jq -r ".[] | select(.id == $QUEUE_ID) | .download_url")
    
    if [ "$PENDING" = "false" ] && [ -n "$DOWNLOAD_URL" ] && [ "$DOWNLOAD_URL" != "" ]; then
        echo "[$(date)] Skip trace complete!"
        break
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    echo "[$(date)] Still processing... (attempt $ATTEMPT/$MAX_ATTEMPTS)"
done

if [ "$PENDING" = "true" ]; then
    echo "ERROR: Skip trace timed out after $MAX_ATTEMPTS attempts"
    exit 1
fi

# Step 5: Download results
echo "[$(date)] Downloading results..."
curl -s "$DOWNLOAD_URL" > "$OUTPUT_FILE"

RESULT_COUNT=$(tail -n +2 "$OUTPUT_FILE" | wc -l)
echo "[$(date)] Downloaded $RESULT_COUNT results to $OUTPUT_FILE"

# Step 6: Generate summary
PHONES_FOUND=$(tail -n +2 "$OUTPUT_FILE" | cut -d',' -f11 | grep -v '^$' | wc -l)
echo "[$(date)] Phone numbers found: $PHONES_FOUND / $RESULT_COUNT"

echo "[$(date)] Pipeline complete!"
echo "Output file: $OUTPUT_FILE"
