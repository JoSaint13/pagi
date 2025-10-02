# Wine Marketing Analytics Platform Integration

This document describes how to use the Panda AGI chat UI as a frontend for the Wine Marketing Analytics Platform.

## Overview

The integration connects two projects:

1. **Panda AGI Chat UI** (`/Users/andreyzherditskiy/work/panda-agi/examples/ui`) - React frontend + FastAPI backend
2. **Wine Marketing Analytics Platform** (`/Users/andreyzherditskiy/work/bc/omt-pai-4`) - PandasAI-powered customer analytics

**Architecture:**
```
User Query → Panda UI → FastAPI Backend → AgentMediator → MarketingAdapter → Wine Marketing Platform
                                                              ↓
                                                    (local mode or HTTP API)
```

## Features

- **Natural Language Queries**: Ask questions about customers in plain English
- **Preset Filters**: Quick access to common customer segments
- **Real-time Streaming**: Results stream to the UI as they're computed
- **Dual Mode Support**:
  - **Local Mode**: Direct Python import (fast, no network overhead)
  - **HTTP Mode**: REST API calls (for distributed deployments)

## Setup Instructions

### Prerequisites

1. **Python 3.11** installed
2. **Wine Marketing Platform** set up at `/Users/andreyzherditskiy/work/bc/omt-pai-4`
3. **OpenAI API Key** for PandasAI queries

### 1. Configure Environment

Edit `/Users/andreyzherditskiy/work/panda-agi/examples/ui/.env`:

```bash
# Enable bridge mode (uses marketing platform instead of default Panda agent)
CHAT_RUNTIME=bridge

# Marketing platform integration settings
MARKETING_MODE=local  # or 'http' for REST API mode
MARKETING_PLATFORM_PATH=/Users/andreyzherditskiy/work/bc/omt-pai-4
MARKETING_API_URL=http://localhost:5001  # for HTTP mode
MARKETING_API_KEY=your_api_key_here      # for HTTP mode

# Required for PandasAI
OPENAI_API_KEY=sk-proj-...
```

### 2. Install Dependencies

The marketing adapter requires `httpx` for HTTP mode (optional):

```bash
cd /Users/andreyzherditskiy/work/panda-agi/examples/ui/backend
pip install httpx  # or add to requirements.txt
```

### 3. Start the Application

**Option A: Using Docker (recommended)**
```bash
cd /Users/andreyzherditskiy/work/panda-agi/examples/ui
./start.sh
```

**Option B: Manual Start**
```bash
# Terminal 1: Start backend
cd /Users/andreyzherditskiy/work/panda-agi/examples/ui/backend
uvicorn main:app --reload --port 8000

# Terminal 2: Start frontend
cd /Users/andreyzherditskiy/work/panda-agi/examples/ui/frontend
npm install
npm run dev
```

### 4. Access the UI

Open browser at: `http://localhost:3000`

## Usage Examples

### Preset Filters

Try these preset queries:

- "VIP customers only"
- "High value customers (Average Order > $300)"
- "Active customers in last 30 days"
- "Frequent buyers (10+ purchases)"
- "Churn risk customers (inactive 90+ days)"

### Custom Natural Language Queries

- "Show me customers in HORECA segment"
- "Find premium customers with turnover over 50,000 CHF"
- "List customers who purchased En Primeur wines"
- "Show me high-value orders over 1,000 CHF"
- "Which customers are at risk of churning?"

### Query Response

The UI displays:

1. **Query Summary**
   - Total customers found
   - Total/average lifetime value
   - Execution time
   - Engine used (fast_path, llm, preset_filter)
   - Tokens consumed (if LLM was used)

2. **Customer Results** (first 20 shown)
   - Customer ID
   - Name
   - Segment
   - Lifetime Value
   - Total Purchases
   - Average Order Value
   - Last Purchase Date

3. **Technical Details**
   - Generated SQL
   - Generated Python code
   - Execution metadata

## Integration Modes

### Local Mode (Recommended)

**Pros:**
- Fast (no network overhead)
- Direct access to data
- Shared cache with platform
- No authentication needed

**Cons:**
- Requires both projects on same machine
- Must be in same Python environment

**Configuration:**
```bash
MARKETING_MODE=local
MARKETING_PLATFORM_PATH=/Users/andreyzherditskiy/work/bc/omt-pai-4
```

### HTTP Mode

**Pros:**
- Platform can run on different server
- Better separation of concerns
- Easier to scale

**Cons:**
- Network latency
- Requires Flask API running
- Authentication required

**Configuration:**
```bash
MARKETING_MODE=http
MARKETING_API_URL=http://localhost:5001
MARKETING_API_KEY=your_api_key_here

# Start Flask API in omt-pai-4:
cd /Users/andreyzherditskiy/work/bc/omt-pai-4
make http  # or: python -m flask --app api run --port 5001
```

## Event Streaming Format

The adapter transforms marketing responses into Panda-compatible events:

```json
{
  "event_type": "tool_end",
  "timestamp": "2025-10-03T12:34:56.789Z",
  "data": {
    "type": "marketing_response",
    "tool_name": "omt.marketing.filter",
    "id": "uuid",
    "timestamp": "2025-10-03T12:34:56.789Z",
    "payload": {
      "query": "VIP customers only",
      "engine_used": "fast_path",
      "tokens_used": 0,
      "execution_time": 0.54,
      "count": 42,
      "customer_ids": ["CUST-001", "CUST-002"],
      "customers": [ { ...CustomerRecord... } ],
      "sql": "SELECT ...",
      "metadata": { ... }
    }
  }
}
```

## Architecture Details

### Components

**`backend/services/marketing_adapter.py`**
- Handles communication with marketing platform
- Supports local (Python import) and HTTP modes
- Transforms responses to standard format

**`backend/services/mediator.py`**
- Bridges Panda UI streaming protocol
- Wraps marketing responses in event envelopes
- Provides summary statistics

**`backend/services/agent.py`**
- Routes requests to mediator when `CHAT_RUNTIME=bridge`
- Handles conversation lifecycle
- Streams events to frontend

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHAT_RUNTIME` | Yes | - | Set to `bridge` to enable integration |
| `MARKETING_MODE` | Yes | `local` | Mode: `local` or `http` |
| `MARKETING_PLATFORM_PATH` | Local mode | - | Path to omt-pai-4 project |
| `MARKETING_API_URL` | HTTP mode | `http://localhost:5001` | Flask API base URL |
| `MARKETING_API_KEY` | HTTP mode | - | API key for authentication |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key for PandasAI |

## Troubleshooting

### "Failed to load marketing platform"

**Cause:** `MARKETING_PLATFORM_PATH` incorrect or missing dependencies

**Solution:**
```bash
# Verify path exists
ls -la /Users/andreyzherditskiy/work/bc/omt-pai-4

# Check Python path
echo $PYTHONPATH

# Install dependencies in omt-pai-4
cd /Users/andreyzherditskiy/work/bc/omt-pai-4
pip install -r requirements.txt
```

### "Marketing query failed: 401 Unauthorized"

**Cause:** Invalid or missing API key in HTTP mode

**Solution:**
```bash
# Check API key in .env
grep MARKETING_API_KEY /Users/andreyzherditskiy/work/panda-agi/examples/ui/.env

# Verify it matches omt-pai-4/.env
grep API_KEY /Users/andreyzherditskiy/work/bc/omt-pai-4/.env
```

### "ModuleNotFoundError: No module named 'agent'"

**Cause:** Marketing platform not in Python path

**Solution:**
```bash
# Option 1: Set PYTHONPATH
export PYTHONPATH=/Users/andreyzherditskiy/work/bc/omt-pai-4:$PYTHONPATH

# Option 2: Use HTTP mode instead
# Edit .env:
MARKETING_MODE=http
```

### Slow Query Performance

**Issue:** Queries taking 5+ seconds

**Solutions:**
1. Use preset filters when possible (zero-cost fast path)
2. Check if DuckDB cache is enabled
3. Monitor token usage in response metadata
4. Consider switching to HTTP mode with cached Flask API

### No Results Returned

**Debugging:**
1. Check backend logs: `docker logs panda-ui-backend`
2. Test marketing platform directly:
   ```bash
   cd /Users/andreyzherditskiy/work/bc/omt-pai-4
   python main.py
   # Try same query
   ```
3. Verify data files exist:
   ```bash
   ls -la /Users/andreyzherditskiy/work/bc/omt-pai-4/dal/data/*.pkl
   ```

## Testing

### Manual Testing

1. **Start UI**: `cd /Users/andreyzherditskiy/work/panda-agi/examples/ui && ./start.sh`
2. **Open browser**: `http://localhost:3000`
3. **Test queries**:
   - Preset filter: "VIP customers only"
   - Custom query: "Show HORECA customers"
   - Invalid query: "nonsense query xyz"
4. **Verify**:
   - Results appear in UI
   - Summary shows correct counts
   - Execution time displayed
   - SQL/code shown in details

### Automated Testing

```bash
# Test adapter directly
cd /Users/andreyzherditskiy/work/panda-agi/examples/ui/backend
python -c "
import asyncio
from services.marketing_adapter import MarketingAdapter

async def test():
    adapter = MarketingAdapter()
    result = await adapter.query('VIP customers only')
    print(f'Success: {result[\"success\"]}')
    print(f'Count: {result[\"count\"]}')
    await adapter.close()

asyncio.run(test())
"
```

## Performance Optimization

### Fast Path Queries (Zero Cost)

These queries use direct pandas operations without LLM:

- "VIP customers only"
- "Premium customers (turnover > 50,000 CHF)"
- "Active customers (purchased after Jan 2024)"
- Segment filters (HORECA, PRIVATE, TRADE)

**Result:** <100ms execution, $0.00 cost

### Cached Queries

Repeat queries use DuckDB cache:

- 80% cost reduction
- <200ms execution
- Enabled by default in local mode

### Token Tracking

Monitor costs via response metadata:
```json
{
  "tokens_used": 1234,
  "engine_used": "llm",
  "execution_time": 2.34
}
```

## Production Deployment

### Docker Compose

See `docker-compose.yml` in `/Users/andreyzherditskiy/work/panda-agi/examples/ui`

**Environment variables in compose:**
```yaml
environment:
  - CHAT_RUNTIME=bridge
  - MARKETING_MODE=http
  - MARKETING_API_URL=http://marketing-api:5001
  - MARKETING_API_KEY=${MARKETING_API_KEY}
  - OPENAI_API_KEY=${OPENAI_API_KEY}
```

### Kubernetes

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: panda-ui-config
data:
  CHAT_RUNTIME: bridge
  MARKETING_MODE: http
  MARKETING_API_URL: http://marketing-service:5001
---
apiVersion: v1
kind: Secret
metadata:
  name: panda-ui-secrets
type: Opaque
stringData:
  MARKETING_API_KEY: your_key
  OPENAI_API_KEY: sk-proj-...
```

## Security Considerations

1. **API Key Protection**: Never commit `.env` files with keys
2. **HTTPS in Production**: Use TLS for HTTP mode
3. **Rate Limiting**: Configure at API gateway
4. **Data Access**: Synthetic data only, not production customer data
5. **Authentication**: Enable GitHub auth in production (see Panda docs)

## Related Documentation

- [Wine Marketing Platform CLAUDE.md](/Users/andreyzherditskiy/work/bc/omt-pai-4/CLAUDE.md)
- [Integration Contract](/Users/andreyzherditskiy/work/panda-agi/integration.md)
- [Panda AGI Docs](https://agi-docs.pandas-ai.com)

## Support

For issues or questions:
1. Check logs: `docker logs panda-ui-backend`
2. Review [Troubleshooting](#troubleshooting) section
3. Test marketing platform independently
4. Verify environment variables

## License

MIT (both projects)
