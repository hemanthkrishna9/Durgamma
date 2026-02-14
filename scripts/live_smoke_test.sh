#!/usr/bin/env bash
# ============================================================
# Live End-to-End Smoke Test — Mission Control Platform
# Tests every major feature against the running backend
# ============================================================

BASE="http://localhost:8000"
PASS=0
FAIL=0
TOTAL=0

green() { echo -e "\033[32m  PASS: $1\033[0m"; PASS=$((PASS+1)); TOTAL=$((TOTAL+1)); }
red()   { echo -e "\033[31m  FAIL: $1 — $2\033[0m"; FAIL=$((FAIL+1)); TOTAL=$((TOTAL+1)); }
header(){ echo -e "\n\033[1;36m=== $1 ===\033[0m"; }

assert_status() {
    local desc="$1" expected="$2" actual="$3"
    if [ "$actual" = "$expected" ]; then
        green "$desc (HTTP $actual)"
    else
        red "$desc" "expected $expected, got $actual"
    fi
}

assert_json() {
    local desc="$1" field="$2" expected="$3" body="$4"
    local actual
    actual=$(echo "$body" | python3 -c "import sys,json; print(json.load(sys.stdin)$field)" 2>/dev/null || echo "__ERR__")
    if [ "$actual" = "$expected" ]; then
        green "$desc ($field=$actual)"
    else
        red "$desc" "$field: expected '$expected', got '$actual'"
    fi
}

assert_json_gte() {
    local desc="$1" field="$2" min="$3" body="$4"
    local actual
    actual=$(echo "$body" | python3 -c "import sys,json; print(json.load(sys.stdin)$field)" 2>/dev/null || echo "0")
    if [ "$actual" -ge "$min" ] 2>/dev/null; then
        green "$desc ($field=$actual >= $min)"
    else
        red "$desc" "$field: expected >= $min, got '$actual'"
    fi
}

# ============================================================
header "1. Health Check"
# ============================================================
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/health")
BODY=$(cat /tmp/mc_body)
assert_status "GET /api/health" 200 "$HTTP"
assert_json "Health status ok" "['status']" "ok" "$BODY"
assert_json "Heartbeat running" "['heartbeat_running']" "True" "$BODY"

# ============================================================
header "2. Authentication"
# ============================================================
# Register
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/auth/register" \
    -H "Content-Type: application/json" \
    -d '{"email":"smoketest@example.com","name":"Smoke Tester","password":"test1234"}')
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/auth/register" 201 "$HTTP"
TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
assert_json "User registered" "['user']['email']" "smoketest@example.com" "$BODY"

# Login
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"smoketest@example.com","password":"test1234"}')
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/auth/login" 200 "$HTTP"

# Get me (authenticated)
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/auth/me" \
    -H "Authorization: Bearer $TOKEN")
BODY=$(cat /tmp/mc_body)
assert_status "GET /api/auth/me (authed)" 200 "$HTTP"
assert_json "Correct user returned" "['name']" "Smoke Tester" "$BODY"

# Get me (no token)
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/auth/me")
assert_status "GET /api/auth/me (no token) → 401" 401 "$HTTP"

# Wrong password
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"smoketest@example.com","password":"wrong"}')
assert_status "POST /api/auth/login (wrong password) → 401" 401 "$HTTP"

# ============================================================
header "3. Mission Lifecycle: Create → Analyze → Approve → Execute"
# ============================================================
# Create mission
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/missions" \
    -H "Content-Type: application/json" \
    -d '{
        "title":"E-Commerce Platform — Smoke Test",
        "goal":"Build a full-stack e-commerce platform with payment processing",
        "customer_name":"SmokeTestCorp",
        "budget_cap":500.0
    }')
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/missions (create)" 201 "$HTTP"
MISSION_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
assert_json "Mission status = intake" "['status']" "intake" "$BODY"
echo "  Mission ID: $MISSION_ID"

# Add specification
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X PATCH "$BASE/api/missions/$MISSION_ID" \
    -H "Content-Type: application/json" \
    -d '{"specification":"React + TypeScript frontend, Python FastAPI backend, PostgreSQL. Stripe payments. JWT auth. Product catalog, cart, orders."}')
assert_status "PATCH /api/missions (add spec)" 200 "$HTTP"

# Analyze
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/missions/$MISSION_ID/analyze")
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/missions/:id/analyze" 200 "$HTTP"
assert_json_gte "Agents planned >= 4" "['agents'].__len__()" 4 "$BODY"
assert_json_gte "Tasks planned >= 3" "['tasks'].__len__()" 3 "$BODY"

# Check planning status
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/missions/$MISSION_ID")
BODY=$(cat /tmp/mc_body)
assert_json "Mission status = planning" "['status']" "planning" "$BODY"

# Approve → spawn agents
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/missions/$MISSION_ID/approve")
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/missions/:id/approve" 200 "$HTTP"
assert_json "Spawn status ok" "['status']" "ok" "$BODY"
AGENTS_CREATED=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['agents_created'])")
TASKS_CREATED=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['tasks_created'])")
echo "  Agents created: $AGENTS_CREATED, Tasks created: $TASKS_CREATED"

# Verify executing
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/missions/$MISSION_ID")
BODY=$(cat /tmp/mc_body)
assert_json "Mission status = executing" "['status']" "executing" "$BODY"

# ============================================================
header "4. Agents"
# ============================================================
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/agents?mission_id=$MISSION_ID")
BODY=$(cat /tmp/mc_body)
assert_status "GET /api/agents" 200 "$HTTP"
assert_json_gte "Agents count >= 4" ".__len__()" 4 "$BODY"

AGENT_A=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'])")
AGENT_B=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[1]['id'])")
echo "  Agent A: $AGENT_A"
echo "  Agent B: $AGENT_B"

# Check individual agent
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/agents/$AGENT_A")
BODY=$(cat /tmp/mc_body)
assert_status "GET /api/agents/:id" 200 "$HTTP"
assert_json "Agent is active" "['status']" "active" "$BODY"

# ============================================================
header "5. Tasks"
# ============================================================
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/tasks?mission_id=$MISSION_ID")
BODY=$(cat /tmp/mc_body)
assert_status "GET /api/tasks" 200 "$HTTP"
assert_json_gte "Tasks count >= 3" ".__len__()" 3 "$BODY"

TASK_ID=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(next(t['id'] for t in d if t['status']=='todo'))")
echo "  First todo task: $TASK_ID"

# Update task to in_progress
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X PATCH "$BASE/api/tasks/$TASK_ID" \
    -H "Content-Type: application/json" \
    -d '{"status":"in_progress","progress":"Working on it..."}')
BODY=$(cat /tmp/mc_body)
assert_status "PATCH /api/tasks/:id (→ in_progress)" 200 "$HTTP"
assert_json "Task in_progress" "['status']" "in_progress" "$BODY"

# Complete task
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X PATCH "$BASE/api/tasks/$TASK_ID" \
    -H "Content-Type: application/json" \
    -d '{"status":"done","output":"Architecture document completed."}')
BODY=$(cat /tmp/mc_body)
assert_status "PATCH /api/tasks/:id (→ done)" 200 "$HTTP"
assert_json "Task done" "['status']" "done" "$BODY"

# Check dependencies
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/tasks/$TASK_ID/dependencies-met")
assert_status "GET /api/tasks/:id/dependencies-met" 200 "$HTTP"

# ============================================================
header "6. Cost Tracking"
# ============================================================
# Record cost
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/cost/record" \
    -H "Content-Type: application/json" \
    -d "{\"mission_id\":\"$MISSION_ID\",\"agent_id\":\"$AGENT_A\",\"model\":\"claude-sonnet-4-20250514\",\"input_tokens\":5000,\"output_tokens\":2000}")
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/cost/record" 200 "$HTTP"

# Cost summary
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/cost/$MISSION_ID/summary")
BODY=$(cat /tmp/mc_body)
assert_status "GET /api/cost/:id/summary" 200 "$HTTP"
assert_json "Record count = 1" "['record_count']" "1" "$BODY"

# Budget status
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/cost/$MISSION_ID/budget")
BODY=$(cat /tmp/mc_body)
assert_status "GET /api/cost/:id/budget" 200 "$HTTP"
assert_json "Budget ok" "['status']" "ok" "$BODY"

# ============================================================
header "7. Approvals"
# ============================================================
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/approvals" \
    -H "Content-Type: application/json" \
    -d "{\"mission_id\":\"$MISSION_ID\",\"gate_type\":\"deploy_staging\",\"title\":\"Deploy to Staging\",\"description\":\"Ready for staging\",\"requested_by\":\"devops\"}")
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/approvals (create)" 201 "$HTTP"
APPROVAL_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
assert_json "Approval pending" "['status']" "pending" "$BODY"

# Approve it
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/approvals/$APPROVAL_ID/decide" \
    -H "Content-Type: application/json" \
    -d '{"status":"approved","comment":"LGTM"}')
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/approvals/:id/decide" 200 "$HTTP"
assert_json "Approval approved" "['status']" "approved" "$BODY"

# List approvals
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/approvals?mission_id=$MISSION_ID")
assert_status "GET /api/approvals" 200 "$HTTP"

# ============================================================
header "8. Conflict Resolution"
# ============================================================
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/conflicts/resolve" \
    -H "Content-Type: application/json" \
    -d "{\"mission_id\":\"$MISSION_ID\",\"agent_a_id\":\"$AGENT_A\",\"agent_b_id\":\"$AGENT_B\",\"domain\":\"api\",\"description\":\"API format disagreement\"}")
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/conflicts/resolve" 200 "$HTTP"

# Divergence check
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/conflicts/$MISSION_ID/divergences")
BODY=$(cat /tmp/mc_body)
assert_status "GET /api/conflicts/:id/divergences" 200 "$HTTP"

# ============================================================
header "9. Heartbeat"
# ============================================================
# Report heartbeat
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/heartbeat/report" \
    -H "Content-Type: application/json" \
    -d "{\"agent_id\":\"$AGENT_A\",\"status\":\"working\",\"tokens_used\":500}")
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/heartbeat/report" 200 "$HTTP"
assert_json "Heartbeat ok" "['status']" "ok" "$BODY"

# Stale agents
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/heartbeat/$MISSION_ID/stale")
BODY=$(cat /tmp/mc_body)
assert_status "GET /api/heartbeat/:id/stale" 200 "$HTTP"

# Service status
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/heartbeat/status")
BODY=$(cat /tmp/mc_body)
assert_status "GET /api/heartbeat/status" 200 "$HTTP"
assert_json "Heartbeat service running" "['running']" "True" "$BODY"

# ============================================================
header "10. Agent Messaging"
# ============================================================
# Send message
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/messages/send" \
    -H "Content-Type: application/json" \
    -d "{\"mission_id\":\"$MISSION_ID\",\"from_agent_id\":\"$AGENT_A\",\"to_agent_id\":\"$AGENT_B\",\"content\":\"Please review the API design\",\"message_type\":\"request\"}")
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/messages/send" 200 "$HTTP"
assert_json "Message sent ok" "['status']" "ok" "$BODY"
MSG_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['message_id'])")

# List messages
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/messages/$MISSION_ID")
BODY=$(cat /tmp/mc_body)
assert_status "GET /api/messages/:mission_id" 200 "$HTTP"
assert_json_gte "Messages count >= 1" ".__len__()" 1 "$BODY"

# Acknowledge
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/messages/$MSG_ID/acknowledge")
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/messages/:id/acknowledge" 200 "$HTTP"

# Unread count
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/messages/$MISSION_ID/unread/$AGENT_B")
BODY=$(cat /tmp/mc_body)
assert_status "GET /api/messages/:mid/unread/:aid" 200 "$HTTP"

# Broadcast
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/messages/broadcast" \
    -H "Content-Type: application/json" \
    -d "{\"mission_id\":\"$MISSION_ID\",\"from_agent_id\":\"$AGENT_A\",\"content\":\"Team update: architecture review complete\",\"message_type\":\"general\"}")
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/messages/broadcast" 200 "$HTTP"
assert_json "Broadcast ok" "['status']" "ok" "$BODY"

# ============================================================
header "11. Events & Activity Feed"
# ============================================================
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/events/$MISSION_ID?limit=100")
BODY=$(cat /tmp/mc_body)
assert_status "GET /api/events/:id" 200 "$HTTP"
assert_json_gte "Events logged >= 5" ".__len__()" 5 "$BODY"

HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/activity/$MISSION_ID?limit=50")
BODY=$(cat /tmp/mc_body)
assert_status "GET /api/activity/:id" 200 "$HTTP"
assert_json_gte "Activity entries >= 1" ".__len__()" 1 "$BODY"

# ============================================================
header "12. Pause / Resume"
# ============================================================
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/missions/$MISSION_ID/pause")
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/missions/:id/pause" 200 "$HTTP"
assert_json_gte "Agents paused >= 1" "['agents_paused']" 1 "$BODY"

HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/missions/$MISSION_ID/resume")
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/missions/:id/resume" 200 "$HTTP"
assert_json_gte "Agents resumed >= 1" "['agents_resumed']" 1 "$BODY"

# ============================================================
header "13. Delivery"
# ============================================================
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/delivery/$MISSION_ID/generate")
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/delivery/:id/generate" 200 "$HTTP"
assert_json "Delivery ok" "['status']" "ok" "$BODY"

HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/missions/$MISSION_ID")
BODY=$(cat /tmp/mc_body)
assert_json "Mission status = delivered" "['status']" "delivered" "$BODY"

# ============================================================
header "14. Terminate"
# ============================================================
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" -X POST "$BASE/api/missions/$MISSION_ID/terminate")
BODY=$(cat /tmp/mc_body)
assert_status "POST /api/missions/:id/terminate" 200 "$HTTP"
assert_json_gte "Agents terminated >= 1" "['agents_terminated']" 1 "$BODY"

HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/api/missions/$MISSION_ID")
BODY=$(cat /tmp/mc_body)
assert_json "Mission status = closed" "['status']" "closed" "$BODY"

# ============================================================
header "15. OpenAPI Schema"
# ============================================================
HTTP=$(curl -s -o /tmp/mc_body -w "%{http_code}" "$BASE/openapi.json")
assert_status "GET /openapi.json" 200 "$HTTP"
ENDPOINTS=$(cat /tmp/mc_body | python3 -c "import sys,json; d=json.load(sys.stdin); print(sum(len(v) for v in d['paths'].values()))")
echo "  Total API endpoints: $ENDPOINTS"

# ============================================================
# RESULTS
# ============================================================
echo ""
echo "============================================================"
if [ $FAIL -eq 0 ]; then
    echo -e "\033[1;32m  ALL $TOTAL TESTS PASSED!\033[0m"
else
    echo -e "\033[1;31m  $FAIL / $TOTAL TESTS FAILED\033[0m"
fi
echo "============================================================"
echo ""

rm -f /tmp/mc_body
exit $FAIL
