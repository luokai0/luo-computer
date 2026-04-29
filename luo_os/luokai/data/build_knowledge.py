#!/usr/bin/env python3
"""
LUOKAI Deep Knowledge Builder
Generates LUOKAI's real brain — thousands of high-quality Q&A pairs
covering every topic a developer would ask about.
"""
import json, os
from pathlib import Path

OUT = Path(__file__).parent / "knowledge"
OUT.mkdir(exist_ok=True)

ALL = []

def add(q, a, cat, lang="general", diff="intermediate"):
    ALL.append({"q": q, "a": a, "c": cat, "l": lang, "d": diff})

# ═══════════════════════════════════════════════════════════════════
# WEB & CSS
# ═══════════════════════════════════════════════════════════════════
add("how to center div in css",
"""CSS centering depends on layout context. The modern way:

**Flexbox (best for most cases):**
```css
.parent {
  display: flex;
  justify-content: center;  /* horizontal */
  align-items: center;      /* vertical */
  height: 100vh;            /* needs height for vertical */
}
```

**Grid:**
```css
.parent {
  display: grid;
  place-items: center;  /* centers both axes */
  height: 100vh;
}
```

**Absolute positioning:**
```css
.child {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
}
```

**Horizontally only:**
```css
.block { margin: 0 auto; width: fit-content; }
```""","css","css","beginner")

add("what is css flexbox",
"""Flexbox is a one-dimensional layout model for arranging items in rows or columns.

```css
.container {
  display: flex;
  flex-direction: row;          /* row | column */
  justify-content: space-between; /* main axis alignment */
  align-items: center;          /* cross axis alignment */
  flex-wrap: wrap;
  gap: 16px;
}
.item {
  flex: 1;           /* grow equally */
  flex: 0 0 200px;   /* fixed 200px */
}
```

**Key properties:**
- `justify-content`: main axis — flex-start, center, flex-end, space-between, space-around
- `align-items`: cross axis — flex-start, center, flex-end, stretch
- `flex`: shorthand for flex-grow, flex-shrink, flex-basis

Use Flexbox for 1D (row or column). Use Grid for 2D (rows AND columns).""","css","css","beginner")

add("what is css grid",
"""CSS Grid is a two-dimensional layout system for rows and columns simultaneously.

```css
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);  /* 3 equal columns */
  grid-template-columns: 200px 1fr 2fr;   /* mixed */
  grid-template-rows: auto 1fr auto;
  gap: 20px;
}

/* Span items */
.header  { grid-column: 1 / -1; }     /* full width */
.sidebar { grid-row: 2 / 4; }         /* span 2 rows */

/* Named areas */
.layout {
  grid-template-areas:
    "header header"
    "sidebar main"
    "footer footer";
}
.header { grid-area: header; }
```

Grid = 2D layout. Flexbox = 1D layout.""","css","css","intermediate")

add("css box model explained",
"""Every HTML element is a box with 4 layers:

```
┌─────────────── margin ───────────────┐
│  ┌─────────── border ──────────────┐ │
│  │  ┌──────── padding ──────────┐  │ │
│  │  │         content           │  │ │
│  │  └───────────────────────────┘  │ │
│  └─────────────────────────────────┘ │
└──────────────────────────────────────┘
```

```css
.box {
  width: 200px;     /* content width */
  padding: 20px;    /* inside border */
  border: 2px solid #000;
  margin: 10px;     /* outside border */
}
/* Total width = 200 + 40 + 4 = 244px (default box-sizing: content-box) */

/* Use this always — width includes padding+border: */
* { box-sizing: border-box; }
/* Now width: 200px = TOTAL width */
```""","css","css","beginner")

add("what is responsive design",
"""Responsive design makes websites work on all screen sizes using CSS.

**Key techniques:**

1. **Media queries** — apply styles at breakpoints:
```css
/* Mobile first */
.container { width: 100%; }

@media (min-width: 768px) {  /* tablet */
  .container { max-width: 768px; }
}
@media (min-width: 1024px) { /* desktop */
  .container { max-width: 1200px; }
}
```

2. **Fluid units** — relative sizes:
```css
font-size: 1rem;      /* relative to root */
width: 80%;           /* relative to parent */
max-width: 1200px;    /* cap on large screens */
padding: 2vw;         /* viewport width */
```

3. **Responsive images:**
```css
img { max-width: 100%; height: auto; }
```

4. **CSS Grid/Flexbox** with `auto-fill`/`minmax`:
```css
grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
```""","css","css","intermediate")

# ═══════════════════════════════════════════════════════════════════
# REST & APIs
# ═══════════════════════════════════════════════════════════════════
add("what is REST API",
"""REST (Representational State Transfer) is an architectural style for APIs using HTTP.

**HTTP methods:**
```
GET    /api/users        → list all users
GET    /api/users/1      → get user with id=1
POST   /api/users        → create new user
PUT    /api/users/1      → replace user 1
PATCH  /api/users/1      → update fields of user 1
DELETE /api/users/1      → delete user 1
```

**Status codes:**
- 200 OK, 201 Created, 204 No Content
- 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found
- 500 Internal Server Error

**RESTful principles:**
- Stateless — each request has all info needed
- Use nouns for resources, not verbs (`/users` not `/getUsers`)
- Nest resources logically (`/users/1/posts`)
- Version your API (`/api/v1/users`)

**Example response:**
```json
{"id": 1, "name": "Alice", "email": "alice@example.com"}
```""","api","general","beginner")

add("what is GraphQL",
"""GraphQL is a query language for APIs where the client specifies exactly what data it needs.

**vs REST:**
- REST: multiple endpoints, fixed response shape
- GraphQL: one endpoint `/graphql`, client defines shape

**Query (fetch data):**
```graphql
query {
  user(id: "1") {
    name
    email
    posts {
      title
      createdAt
    }
  }
}
```

**Mutation (change data):**
```graphql
mutation {
  createUser(input: { name: "Alice", email: "a@b.com" }) {
    id
    name
  }
}
```

**Advantages:** No over-fetching, no under-fetching, strongly typed schema, self-documenting.
**Disadvantages:** More complex caching, harder to optimize on server side.

Use GraphQL when: frontend needs flexible queries, multiple clients with different data needs.""","api","general","intermediate")

add("what is WebSocket",
"""WebSocket is a protocol for full-duplex (two-way) real-time communication over a single TCP connection.

**vs HTTP:**
- HTTP: client requests → server responds (one-way per request)
- WebSocket: persistent connection, server can push data anytime

**Use cases:** chat apps, live dashboards, collaborative editing, games, stock tickers.

**JavaScript client:**
```javascript
const ws = new WebSocket('wss://example.com/socket');

ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'join', room: 'general' }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};

ws.onclose = () => console.log('Disconnected');
ws.onerror = (err) => console.error('Error:', err);
```

**Python server (websockets library):**
```python
import asyncio, websockets, json

async def handler(websocket):
    async for message in websocket:
        data = json.loads(message)
        await websocket.send(json.dumps({"echo": data}))

asyncio.run(websockets.serve(handler, "localhost", 8765))
```""","api","general","intermediate")

add("what is OAuth",
"""OAuth 2.0 is an authorization framework that lets users grant apps access to their data without sharing passwords.

**Flow (Authorization Code — most common):**
```
1. User clicks "Login with Google"
2. App redirects to Google: GET /oauth/authorize?client_id=...&redirect_uri=...&scope=email
3. User logs in and approves
4. Google redirects back: GET /callback?code=AUTHCODE
5. App exchanges code for token: POST /oauth/token {code, client_secret}
6. Google returns: {"access_token": "...", "expires_in": 3600}
7. App uses token: GET /userinfo with Authorization: Bearer TOKEN
```

**Key concepts:**
- **Access Token** — short-lived token to access resources
- **Refresh Token** — long-lived token to get new access tokens
- **Scope** — what permissions are granted (email, profile, etc.)
- **Client ID/Secret** — app credentials (secret stays on server!)

**OAuth vs Auth:**
- OAuth = authorization (what can you access)
- JWT/session = authentication (who are you)

Modern apps often use OAuth + OpenID Connect (OIDC) together.""","auth","general","intermediate")

add("what is JWT",
"""JWT (JSON Web Token) is a compact, self-contained token for securely transmitting information.

**Structure:** `header.payload.signature` (base64 encoded, dot-separated)

```
eyJhbGciOiJIUzI1NiJ9.eyJ1c2VySWQiOjEsImV4cCI6MTcwMH0.abc123
    header                    payload                    signature
```

**Payload contains claims:**
```json
{"userId": 1, "email": "alice@example.com", "exp": 1700000000, "iat": 1699000000}
```

**Python usage:**
```python
import jwt

SECRET = "your-secret-key"

# Create token
token = jwt.encode({"userId": 1, "exp": time() + 3600}, SECRET, algorithm="HS256")

# Verify token
try:
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    user_id = payload["userId"]
except jwt.ExpiredSignatureError:
    raise Exception("Token expired")
except jwt.InvalidTokenError:
    raise Exception("Invalid token")
```

**Send in HTTP header:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...
```

JWT is stateless — no DB lookup needed to verify. Store in httpOnly cookie (safer) or localStorage.""","auth","general","intermediate")

# ═══════════════════════════════════════════════════════════════════
# DOCKER & DEVOPS
# ═══════════════════════════════════════════════════════════════════
add("explain docker containers",
"""Docker packages apps into containers — isolated environments with everything needed to run.

**Key concepts:**
- **Image** — blueprint (like a class)
- **Container** — running instance (like an object)
- **Dockerfile** — instructions to build an image
- **Registry** — store for images (Docker Hub, ECR)

**Dockerfile:**
```dockerfile
FROM python:3.12-slim          # base image
WORKDIR /app                   # working directory
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "app.py"]
```

**Common commands:**
```bash
docker build -t myapp:1.0 .    # build image
docker run -p 8080:8000 myapp  # run (host:container port)
docker run -d myapp            # run detached (background)
docker ps                      # list running containers
docker logs <id>               # view logs
docker exec -it <id> bash      # shell into container
docker stop <id>               # stop container
docker rm <id>                 # remove container
docker rmi myapp               # remove image
```

**docker-compose (multi-container):**
```yaml
services:
  web:
    build: .
    ports: ["8000:8000"]
    depends_on: [db]
  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: secret
```
Run: `docker-compose up`""","devops","general","intermediate")

add("what is kubernetes",
"""Kubernetes (K8s) orchestrates containers at scale across multiple machines.

**Why K8s:** Docker runs containers on one machine. K8s manages containers across many machines with auto-scaling, self-healing, and load balancing.

**Core objects:**
```yaml
# Pod — smallest unit, one or more containers
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: app
    image: myapp:1.0

# Deployment — manages pods, handles rolling updates
apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 3            # run 3 copies
  selector:
    matchLabels: {app: myapp}
  template:
    spec:
      containers:
      - name: app
        image: myapp:1.0
        resources:
          requests: {memory: "64Mi", cpu: "250m"}
          limits:   {memory: "128Mi", cpu: "500m"}

# Service — stable network endpoint for pods
apiVersion: v1
kind: Service
spec:
  selector: {app: myapp}
  ports: [{port: 80, targetPort: 8000}]
  type: LoadBalancer
```

**Commands:**
```bash
kubectl apply -f deployment.yaml
kubectl get pods
kubectl logs <pod>
kubectl scale deployment myapp --replicas=5
kubectl rollout undo deployment myapp
```""","devops","general","advanced")

add("what is CI CD",
"""CI/CD automates building, testing, and deploying code.

**CI (Continuous Integration):** Auto-build and test on every commit.
**CD (Continuous Delivery/Deployment):** Auto-deploy after tests pass.

**GitHub Actions example:**
```yaml
# .github/workflows/ci.yml
name: CI/CD
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install -r requirements.txt
      - run: pytest --cov=src
      - run: ruff check .

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        env:
          DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
        run: |
          ssh user@server 'cd /app && git pull && systemctl restart app'
```

**Benefits:** Catch bugs early, consistent deployments, faster release cycles, team confidence.""","devops","general","intermediate")

add("git rebase vs merge",
"""Both integrate changes from one branch to another — differently.

**Merge** — creates a merge commit, preserves history:
```bash
git checkout main
git merge feature-branch
# Creates: A---B---M (M = merge commit joining both branches)
```

**Rebase** — replays commits linearly, cleaner history:
```bash
git checkout feature-branch
git rebase main
# Replays feature commits ON TOP of latest main
# Result: A---B---C' (linear, no merge commit)
```

**Interactive rebase** — rewrite history:
```bash
git rebase -i HEAD~3    # last 3 commits
# Opens editor:
# pick a1b2c3 Add login
# squash d4e5f6 Fix typo  ← fold into previous
# reword g7h8i9 WIP       ← edit message
```

**When to use:**
- **Merge**: public/shared branches, preserving context
- **Rebase**: local feature branches before PR, clean linear history

**Golden rule:** Never rebase commits already pushed to a shared branch — it rewrites history and breaks others' work.""","git","general","intermediate")

add("how git works internally",
"""Git stores snapshots, not diffs. Every commit is a pointer to a tree of file contents.

**Object types:**
- **blob** — file contents
- **tree** — directory (list of blobs + trees)
- **commit** — snapshot + parent + author + message
- **tag** — named reference to a commit

**SHA-1 hash** — every object has a unique 40-char hash based on content.

```bash
git cat-file -t abc123   # type: commit/blob/tree
git cat-file -p abc123   # print contents

# A commit looks like:
# tree 9f3a...
# parent 1b2c...
# author Alice <a@b.com> 1700000000 +0000
# committer Alice <a@b.com> 1700000000 +0000
# Add login feature
```

**Branches** are just files containing a commit hash:
```bash
cat .git/refs/heads/main   # abc123def456...
```

**HEAD** points to current branch:
```bash
cat .git/HEAD    # ref: refs/heads/main
```

**Staging area (index)** is a binary file at `.git/index` — it's the proposed next commit.""","git","general","advanced")

# ═══════════════════════════════════════════════════════════════════
# ALGORITHMS & COMPUTER SCIENCE
# ═══════════════════════════════════════════════════════════════════
add("what is recursion",
"""Recursion is when a function calls itself with a smaller version of the problem.

**Two requirements:**
1. **Base case** — stops the recursion
2. **Recursive case** — reduces the problem

```python
# Factorial: n! = n × (n-1)!
def factorial(n):
    if n <= 1:         # base case
        return 1
    return n * factorial(n - 1)  # recursive case

factorial(5) = 5 × factorial(4)
             = 5 × 4 × factorial(3)
             = 5 × 4 × 3 × factorial(2)
             = 5 × 4 × 3 × 2 × factorial(1)
             = 5 × 4 × 3 × 2 × 1 = 120

# Tree traversal — naturally recursive
def inorder(node):
    if node is None:   # base case
        return []
    return inorder(node.left) + [node.val] + inorder(node.right)
```

**When to use:**
✅ Problem is naturally recursive (trees, graphs, fractals, divide-and-conquer)
✅ Recursive solution is significantly clearer than iterative
❌ Deep recursion risks stack overflow (use iteration or increase limit)
❌ Overlapping subproblems without memoization (exponential time)

**Always add memoization for overlapping subproblems:**
```python
from functools import lru_cache

@lru_cache(maxsize=None)
def fib(n):
    if n < 2: return n
    return fib(n-1) + fib(n-2)
```""","algorithms","general","intermediate")

add("explain big o notation",
"""Big O describes how runtime or space grows as input size (n) grows. Worst case.

**Common complexities (fastest → slowest):**
```
O(1)        Constant    — array[index], dict lookup, stack push/pop
O(log n)    Logarithmic — binary search, balanced BST lookup
O(n)        Linear      — linear search, single loop
O(n log n)  Linearithmic— merge sort, heap sort, good sorting
O(n²)       Quadratic   — nested loops, bubble sort
O(2^n)      Exponential — recursive Fibonacci, subsets
O(n!)       Factorial   — permutations, brute force TSP
```

**Rules:**
- Drop constants: O(2n) → O(n)
- Drop lower terms: O(n² + n) → O(n²)
- Focus on worst case (usually)

**Examples:**
```python
# O(1) — constant, doesn't depend on n
def get_first(lst): return lst[0]

# O(n) — one loop through n items
def find(lst, target):
    for x in lst:          # runs n times
        if x == target: return True

# O(n²) — nested loops
def has_duplicates(lst):
    for i in range(len(lst)):        # n times
        for j in range(i+1, len(lst)): # n times
            if lst[i] == lst[j]: return True

# O(log n) — halving search space each time
def binary_search(arr, target):
    l, r = 0, len(arr)-1
    while l <= r:
        m = (l+r)//2
        if arr[m] == target: return m
        elif arr[m] < target: l = m+1
        else: r = m-1
```""","algorithms","general","intermediate")

add("what is a hash table",
"""A hash table (dict/hashmap) maps keys to values with O(1) average lookup.

**How it works:**
1. Hash function converts key to array index
2. Value stored at that index
3. Collision handling when two keys map to same index

```python
# Python dict IS a hash table
d = {"alice": 30, "bob": 25}
d["alice"]    # O(1) — hash("alice") → index → value
d["charlie"]  # O(1) — KeyError if missing
d.get("x", 0) # O(1) — safe with default

# Building from scratch:
class HashTable:
    def __init__(self, size=64):
        self.buckets = [[] for _ in range(size)]

    def _hash(self, key):
        return hash(key) % len(self.buckets)

    def set(self, key, value):
        bucket = self.buckets[self._hash(key)]
        for i, (k, v) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)  # update
                return
        bucket.append((key, value))       # insert

    def get(self, key, default=None):
        for k, v in self.buckets[self._hash(key)]:
            if k == key: return v
        return default
```

**Time complexity:** O(1) average, O(n) worst case (all keys collide).
**Load factor:** items/buckets. Rehash when > 0.75.
**Keys must be hashable** — strings, numbers, tuples. Not lists.""","algorithms","general","intermediate")

add("what is a linked list",
"""A linked list is a sequence of nodes where each node holds data and a pointer to the next node.

```python
class Node:
    def __init__(self, val):
        self.val = val
        self.next = None   # pointer to next node

class LinkedList:
    def __init__(self):
        self.head = None

    def append(self, val):          # O(n)
        new = Node(val)
        if not self.head:
            self.head = new; return
        cur = self.head
        while cur.next: cur = cur.next
        cur.next = new

    def prepend(self, val):         # O(1)
        new = Node(val)
        new.next = self.head
        self.head = new

    def delete(self, val):          # O(n)
        if not self.head: return
        if self.head.val == val:
            self.head = self.head.next; return
        cur = self.head
        while cur.next:
            if cur.next.val == val:
                cur.next = cur.next.next; return
            cur = cur.next

    def to_list(self):
        result, cur = [], self.head
        while cur: result.append(cur.val); cur = cur.next
        return result
```

**vs Arrays:**
- Linked list: O(1) insert/delete at head, O(n) access by index
- Array: O(1) access by index, O(n) insert/delete middle

Use when: frequent inserts/deletes at head, unknown size, implementing queues/stacks.""","algorithms","general","intermediate")

add("explain depth first search dfs",
"""DFS explores as deep as possible down each branch before backtracking.

```python
# Graph DFS — iterative (stack)
def dfs(graph, start):
    visited = set()
    stack = [start]
    result = []
    while stack:
        node = stack.pop()           # LIFO
        if node not in visited:
            visited.add(node)
            result.append(node)
            stack.extend(graph[node]) # add neighbors
    return result

# Graph DFS — recursive
def dfs_recursive(graph, node, visited=None):
    if visited is None: visited = set()
    visited.add(node)
    for neighbor in graph[node]:
        if neighbor not in visited:
            dfs_recursive(graph, neighbor, visited)
    return visited

# Binary tree DFS (inorder)
def inorder(root):
    if not root: return []
    return inorder(root.left) + [root.val] + inorder(root.right)
```

**Use DFS for:**
- Detecting cycles
- Topological sort
- Finding connected components
- Maze/path solving (backtracking)
- Tree traversals

**Use BFS instead when:** finding shortest path (unweighted), level-order traversal, finding closest node.""","algorithms","general","intermediate")

add("explain breadth first search bfs",
"""BFS explores all neighbors at current depth before going deeper — level by level.

```python
from collections import deque

def bfs(graph, start):
    visited = set([start])
    queue = deque([start])          # FIFO
    result = []
    while queue:
        node = queue.popleft()       # take from front
        result.append(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)  # add to back
    return result

# Shortest path (unweighted)
def shortest_path(graph, start, end):
    queue = deque([(start, [start])])
    visited = {start}
    while queue:
        node, path = queue.popleft()
        if node == end: return path
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return None  # no path

# Level-order tree traversal
def level_order(root):
    if not root: return []
    result, queue = [], deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):   # process one level
            node = queue.popleft()
            level.append(node.val)
            if node.left:  queue.append(node.left)
            if node.right: queue.append(node.right)
        result.append(level)
    return result
```

**Use BFS for:** shortest path (unweighted), level-order traversal, finding closest node.""","algorithms","general","intermediate")

# ═══════════════════════════════════════════════════════════════════
# SYSTEM DESIGN & ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════
add("explain microservices",
"""Microservices split an application into small, independent services that communicate over a network.

**vs Monolith:**
```
Monolith:                    Microservices:
┌─────────────────┐          ┌───────┐ ┌───────┐ ┌───────┐
│   Single App    │          │ Users │ │Orders │ │Payment│
│  ┌─────────┐   │          └───┬───┘ └───┬───┘ └───┬───┘
│  │ Users   │   │              │         │         │
│  │ Orders  │   │          ┌───▼─────────▼─────────▼───┐
│  │ Payment │   │          │      API Gateway            │
└─────────────────┘          └─────────────────────────────┘
```

**Benefits:**
- Independent deployment and scaling
- Technology freedom per service
- Fault isolation (one service fails, others keep running)
- Small teams own individual services

**Challenges:**
- Network latency between services
- Distributed tracing and debugging
- Data consistency across services
- More infrastructure complexity

**Communication:**
- **Sync:** REST, gRPC (request-response)
- **Async:** Message queue (RabbitMQ, Kafka) — decoupled, resilient

**When to use:** Large teams, need independent scaling, different tech stacks.
**Start with a monolith** — extract microservices when pain points emerge.""","architecture","general","advanced")

add("what is a message queue",
"""A message queue decouples services — producers send messages, consumers process them asynchronously.

```
Producer → [Queue] → Consumer
           (buffer)

vs synchronous:
Producer → Consumer (waits for response)
```

**Benefits:**
- Decoupling — producer doesn't need consumer to be running
- Load leveling — queue absorbs traffic spikes
- Retry logic — failed messages can be requeued
- Fan-out — one message → multiple consumers

**RabbitMQ (Python):**
```python
import pika

# Producer
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='tasks', durable=True)
channel.basic_publish(
    exchange='',
    routing_key='tasks',
    body='{"user_id": 1, "action": "send_email"}',
    properties=pika.BasicProperties(delivery_mode=2)  # persistent
)

# Consumer
def callback(ch, method, properties, body):
    data = json.loads(body)
    send_email(data['user_id'])
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue='tasks', on_message_callback=callback)
channel.start_consuming()
```

**Use cases:** Email sending, image processing, notifications, payment processing, any async task.""","architecture","general","intermediate")

add("what is caching",
"""Caching stores copies of expensive results so future requests are served faster.

**Cache levels:**
```
Browser cache → CDN → Load Balancer → App cache (Redis) → DB
   fastest                                                slowest
```

**Redis caching (Python):**
```python
import redis, json
from functools import wraps

r = redis.Redis(host='localhost', port=6379)

def cache(ttl=300):  # 5 min default
    def decorator(func):
        @wraps(func)
        def wrapper(*args):
            key = f"{func.__name__}:{args}"
            cached = r.get(key)
            if cached:
                return json.loads(cached)    # cache hit
            result = func(*args)
            r.setex(key, ttl, json.dumps(result))  # cache miss → store
            return result
        return wrapper
    return decorator

@cache(ttl=600)
def get_user(user_id):
    return db.query("SELECT * FROM users WHERE id=?", user_id)
```

**Cache invalidation strategies:**
- **TTL** — expire after time (simple, may serve stale)
- **Write-through** — update cache on every write (consistent, slower writes)
- **Cache-aside** — read from cache, miss → DB → update cache (most common)
- **Invalidate on write** — delete cache key when data changes

**Cache what:** expensive DB queries, computed results, API responses, session data.""","architecture","general","intermediate")

add("what is load balancing",
"""Load balancing distributes incoming traffic across multiple servers.

```
Clients → [Load Balancer] → Server 1
                          → Server 2
                          → Server 3
```

**Algorithms:**
- **Round Robin** — rotate through servers in order (simple, most common)
- **Least Connections** — send to server with fewest active connections
- **IP Hash** — same client always hits same server (session affinity)
- **Weighted** — send more traffic to more powerful servers

**nginx config:**
```nginx
upstream backend {
    least_conn;                    # algorithm
    server 192.168.1.1:8000;
    server 192.168.1.2:8000;
    server 192.168.1.3:8000;
}
server {
    location / {
        proxy_pass http://backend;
    }
}
```

**Health checks:**
```nginx
upstream backend {
    server 192.168.1.1:8000;
    server 192.168.1.2:8000 backup;  # only if others fail
}
```

**Types:**
- **L4 (TCP)** — route by IP/port, fast, no content awareness
- **L7 (HTTP)** — route by URL, headers, content — more flexible""","architecture","general","intermediate")

# ═══════════════════════════════════════════════════════════════════
# DATABASES
# ═══════════════════════════════════════════════════════════════════
add("sql vs nosql databases",
"""**SQL (Relational):** Tables with fixed schema, ACID transactions, powerful joins.
**NoSQL:** Flexible schema, horizontal scaling, multiple data models.

**SQL — use when:**
- Data has clear relationships (users → orders → products)
- Need ACID transactions (banking, e-commerce)
- Complex queries with joins
- Examples: PostgreSQL, MySQL, SQLite

**NoSQL types:**
```
Document (MongoDB):   {"user": "Alice", "orders": [...]}
Key-Value (Redis):    "session:abc" → {user_id: 1, ...}
Column (Cassandra):   Optimized for time-series, analytics
Graph (Neo4j):        Nodes and relationships (social networks)
```

**PostgreSQL example:**
```sql
SELECT u.name, COUNT(o.id) as order_count, SUM(o.total) as revenue
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.created_at > '2024-01-01'
GROUP BY u.id, u.name
HAVING SUM(o.total) > 1000
ORDER BY revenue DESC;
```

**MongoDB example:**
```python
db.users.find({"age": {"$gte": 18}}, {"name": 1, "email": 1})
db.orders.aggregate([
    {"$group": {"_id": "$user_id", "total": {"$sum": "$amount"}}}
])
```

Modern apps often use both — PostgreSQL for transactional data, Redis for caching, Elasticsearch for search.""","databases","general","intermediate")

add("what are database indexes",
"""An index is a data structure (usually B-tree) that speeds up data retrieval at the cost of storage and write speed.

**Without index:** Full table scan O(n) — reads every row.
**With index:** B-tree lookup O(log n) — jumps directly to matching rows.

```sql
-- Create indexes
CREATE INDEX idx_email ON users(email);
CREATE INDEX idx_compound ON orders(user_id, created_at DESC);
CREATE UNIQUE INDEX idx_username ON users(username);

-- Partial index (only index relevant rows)
CREATE INDEX idx_pending ON orders(created_at) WHERE status = 'pending';

-- Check if index is being used
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 1;
-- Look for: "Index Scan" (good) vs "Seq Scan" (may need index)
```

**When to index:**
✅ Columns in WHERE, JOIN, ORDER BY clauses
✅ High cardinality (many unique values — email, user_id)
✅ Foreign keys

**When NOT to index:**
❌ Small tables (full scan is fine)
❌ Write-heavy tables (indexes slow INSERT/UPDATE)
❌ Low cardinality (boolean, status with 3 values)

**Compound index column order matters:**
```sql
-- Index (user_id, status, date)
WHERE user_id = 1                     -- uses index ✅
WHERE user_id = 1 AND status = 'x'   -- uses index ✅
WHERE status = 'x'                    -- can't use index ❌ (no leading col)
```""","databases","sql","intermediate")

add("what is database normalization",
"""Normalization organizes database tables to reduce redundancy and improve integrity.

**1NF — First Normal Form:**
- Each column has atomic (single) values
- No repeating groups

```sql
-- Violates 1NF (multiple values in one column):
users: id | name  | phones
       1  | Alice | 555-1234, 555-5678

-- 1NF compliant:
users: id | name    phones: user_id | phone
       1  | Alice            1      | 555-1234
                             1      | 555-5678
```

**2NF — No partial dependencies** (non-key column depends on full primary key):
```sql
-- Violates 2NF (category_name depends only on category_id, not full key):
order_items: order_id | product_id | quantity | category_name
-- Fix: separate categories table
```

**3NF — No transitive dependencies** (non-key columns depend only on primary key):
```sql
-- Violates 3NF (city → zip_code dependency):
users: id | name | city | zip_code
-- Fix: separate zip_code table or accept denormalization
```

**In practice:**
- 3NF is the target for OLTP (transactional) databases
- Denormalize for read performance (OLAP/reporting)
- Always use foreign keys to maintain referential integrity""","databases","sql","intermediate")

# ═══════════════════════════════════════════════════════════════════
# MACHINE LEARNING & AI
# ═══════════════════════════════════════════════════════════════════
add("what is machine learning",
"""Machine learning is teaching computers to learn from data instead of explicit programming.

**Types:**
- **Supervised** — learns from labeled examples (input → correct output)
- **Unsupervised** — finds patterns in unlabeled data (clustering)
- **Reinforcement** — learns by trial and error with rewards

**Supervised learning workflow:**
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pandas as pd

# 1. Load and prepare data
df = pd.read_csv('data.csv')
X = df.drop('label', axis=1)  # features
y = df['label']                # target

# 2. Split train/test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# 3. Train model
model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)

# 4. Evaluate
y_pred = model.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, y_pred):.2%}")

# 5. Predict new data
model.predict([[feature1, feature2, feature3]])
```

**Key algorithms:**
- Linear/Logistic Regression — simple, interpretable
- Decision Trees / Random Forests — good general purpose
- Gradient Boosting (XGBoost) — often wins competitions
- Neural Networks — images, text, complex patterns""","ml","general","beginner")

add("what is a neural network",
"""A neural network is a system of interconnected nodes (neurons) organized in layers that learns patterns from data.

```
Input Layer → Hidden Layers → Output Layer
  [x1]           [h1]           [y1]
  [x2]     →     [h2]     →     [y2]
  [x3]           [h3]
```

**PyTorch example:**
```python
import torch
import torch.nn as nn

class Network(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(784, 256),   # input → hidden
            nn.ReLU(),             # activation function
            nn.Dropout(0.2),       # regularization
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 10),    # hidden → output (10 classes)
        )

    def forward(self, x):
        return self.layers(x)

model = Network()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
criterion = nn.CrossEntropyLoss()

# Training loop
for epoch in range(10):
    for X_batch, y_batch in dataloader:
        optimizer.zero_grad()
        output = model(X_batch)
        loss = criterion(output, y_batch)
        loss.backward()          # compute gradients
        optimizer.step()         # update weights
```

**Key concepts:**
- **Weights** — learnable parameters
- **Activation functions** — ReLU, Sigmoid, Tanh (add non-linearity)
- **Backpropagation** — how gradients flow backward to update weights
- **Epochs** — number of times we train on the full dataset""","ml","python","advanced")

# ═══════════════════════════════════════════════════════════════════
# NETWORKING & PROTOCOLS
# ═══════════════════════════════════════════════════════════════════
add("how does tcp ip work",
"""TCP/IP is the foundation of internet communication — a 4-layer model.

**Layers (top to bottom):**
```
Application   HTTP, HTTPS, WebSocket, DNS, SMTP
Transport     TCP (reliable) | UDP (fast, unreliable)
Internet      IP — routing packets across networks
Network       Ethernet, WiFi — physical transmission
```

**TCP — Transmission Control Protocol:**
- Connection-oriented (3-way handshake: SYN → SYN-ACK → ACK)
- Guaranteed delivery — resends lost packets
- Ordered — packets arrive in sequence
- Slower but reliable — web, email, file transfer

**UDP — User Datagram Protocol:**
- Connectionless — just send packets, no handshake
- No guarantee of delivery or order
- Fast — gaming, video streaming, DNS, VoIP

**IP Addressing:**
```
IPv4: 192.168.1.1 (32-bit, ~4B addresses)
IPv6: 2001:0db8:85a3::8a2e:0370:7334 (128-bit, virtually unlimited)

Private ranges (not routable on internet):
  10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
```

**DNS resolution:**
```
User types google.com
→ Check local cache
→ Check /etc/hosts
→ Ask ISP's DNS resolver
→ Ask root nameserver → .com nameserver → google.com nameserver
→ Returns 142.250.80.46
→ Browser connects to 142.250.80.46:443 (HTTPS)
```""","networking","general","intermediate")

add("what is https and ssl tls",
"""HTTPS = HTTP + TLS encryption. All data between client and server is encrypted.

**TLS Handshake (simplified):**
```
Client                          Server
  │── ClientHello ──────────────►│  (supported cipher suites)
  │◄─ ServerHello ──────────────│  (chosen cipher + certificate)
  │◄─ Certificate ──────────────│  (server's public key)
  │── ClientKeyExchange ────────►│  (encrypted session key)
  │── Finished ─────────────────►│
  │◄─ Finished ─────────────────│
  │═══════ Encrypted Data ═══════│
```

**Certificate (SSL cert):**
- Proves server identity (signed by trusted CA)
- Contains server's public key
- Has expiry date (typically 90 days with Let's Encrypt)

**HTTPS in Python:**
```python
import requests

# Verify SSL by default
response = requests.get('https://api.example.com/data')

# Custom cert
response = requests.get('https://api.example.com', verify='/path/to/cert.pem')

# Self-signed cert (development only, never production)
response = requests.get('https://localhost:8443', verify=False)
```

**nginx HTTPS config:**
```nginx
server {
    listen 443 ssl http2;
    ssl_certificate     /etc/ssl/certs/example.com.pem;
    ssl_certificate_key /etc/ssl/private/example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
}
```
Let's Encrypt = free SSL certs. Use `certbot` to auto-renew.""","networking","general","intermediate")

# ═══════════════════════════════════════════════════════════════════
# PYTHON ADVANCED
# ═══════════════════════════════════════════════════════════════════
add("what is a python metaclass",
"""A metaclass is the class of a class — it controls how classes are created.

```python
# Normal class creation
class MyClass:
    pass
# Python internally does: MyClass = type('MyClass', (), {})

# Custom metaclass
class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Database(metaclass=SingletonMeta):
    def __init__(self):
        self.connection = connect_to_db()

db1 = Database()
db2 = Database()
print(db1 is db2)  # True — same instance!

# Metaclass that auto-adds logging to all methods
class LoggingMeta(type):
    def __new__(mcs, name, bases, namespace):
        for key, value in namespace.items():
            if callable(value) and not key.startswith('_'):
                namespace[key] = mcs._add_logging(value)
        return super().__new__(mcs, name, bases, namespace)

    @staticmethod
    def _add_logging(func):
        import functools
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            print(f"Calling {func.__name__}")
            return func(*args, **kwargs)
        return wrapper
```

Metaclasses are advanced. Common uses: ORMs (Django models), API frameworks, singleton pattern, auto-registration.""","python","python","advanced")

add("python memory management",
"""Python uses reference counting + cyclic garbage collector.

**Reference counting:**
```python
import sys

x = [1, 2, 3]      # ref count = 1
y = x               # ref count = 2
del x               # ref count = 1
del y               # ref count = 0 → freed immediately
```

**Cyclic references (not caught by ref counting):**
```python
a = {}; b = {}
a['other'] = b
b['other'] = a     # a → b → a cycle
del a; del b        # ref counts both = 1, never reach 0!
# gc module catches these
import gc; gc.collect()
```

**Memory optimization:**
```python
# __slots__ saves memory for many instances
class Point:
    __slots__ = ('x', 'y')   # no __dict__, ~5x less memory
    def __init__(self, x, y):
        self.x = x; self.y = y

# Generators save memory for large sequences
def read_large_file(path):
    with open(path) as f:
        for line in f:     # one line in memory at a time
            yield line.strip()

# Use array module for numeric data (vs list)
import array
nums = array.array('i', range(1000000))  # much smaller than list

# Profile memory
from memory_profiler import profile
@profile
def my_function(): ...
```""","python","python","advanced")

add("python decorators in depth",
"""Decorators are functions that wrap other functions. They use closure and higher-order functions.

**Basic decorator:**
```python
import functools

def my_decorator(func):
    @functools.wraps(func)  # preserves __name__, __doc__
    def wrapper(*args, **kwargs):
        print(f"Before {func.__name__}")
        result = func(*args, **kwargs)
        print(f"After {func.__name__}")
        return result
    return wrapper

@my_decorator
def say_hello(name): return f"Hello {name}"
# Equivalent to: say_hello = my_decorator(say_hello)
```

**Decorator with arguments:**
```python
def repeat(times):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(3)
def greet(): print("Hi!")
greet()  # prints "Hi!" 3 times
```

**Class decorator:**
```python
class Cache:
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self._cache = {}

    def __call__(self, *args):
        if args not in self._cache:
            self._cache[args] = self.func(*args)
        return self._cache[args]

@Cache
def fibonacci(n):
    if n < 2: return n
    return fibonacci(n-1) + fibonacci(n-2)
```

**Stacking decorators:**
```python
@decorator1   # applied last (outermost)
@decorator2   # applied first
def func(): pass
# Equivalent to: func = decorator1(decorator2(func))
```""","python","python","advanced")

# ═══════════════════════════════════════════════════════════════════
# SECURITY
# ═══════════════════════════════════════════════════════════════════
add("how to prevent sql injection",
"""SQL injection happens when user input is embedded directly in SQL queries.

**Vulnerable:**
```python
# NEVER do this
name = request.args.get('name')
query = f"SELECT * FROM users WHERE name = '{name}'"
# Attacker sends: name = ' OR '1'='1
# Query becomes: SELECT * FROM users WHERE name = '' OR '1'='1'
# Returns ALL users!
```

**Safe — parameterized queries:**
```python
# SQLite / sqlite3
cursor.execute("SELECT * FROM users WHERE name = ?", (name,))

# PostgreSQL / psycopg2
cursor.execute("SELECT * FROM users WHERE name = %s", (name,))

# MySQL / pymysql
cursor.execute("SELECT * FROM users WHERE name = %s", (name,))

# SQLAlchemy ORM (always safe)
users = session.query(User).filter(User.name == name).all()

# SQLAlchemy raw query (still safe with bindparams)
result = session.execute(
    text("SELECT * FROM users WHERE name = :name"),
    {"name": name}
)
```

**Additional protections:**
- Use ORM where possible
- Principle of least privilege — DB user only has needed permissions
- Input validation — reject unexpected characters early
- WAF (Web Application Firewall) for extra layer""","security","python","intermediate")

add("how to hash passwords securely",
"""Never store plaintext passwords. Use a slow hashing algorithm designed for passwords.

**Python with bcrypt (recommended):**
```python
import bcrypt

# Hash password (slow by design — ~100ms)
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)  # 12 = work factor
    return bcrypt.hashpw(password.encode(), salt).decode()

# Verify password
def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# Usage
hashed = hash_password("user_password_123")
# Store hashed in database

is_valid = verify_password("user_password_123", hashed)  # True
is_valid = verify_password("wrong_password", hashed)     # False
```

**Python with Argon2 (modern best practice):**
```python
from argon2 import PasswordHasher

ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)

hashed = ph.hash("password")
ph.verify(hashed, "password")  # True or raises exception
```

**Why NOT to use:**
- MD5, SHA-1, SHA-256 — too fast, GPU crackable
- Plain bcrypt without work factor tuning
- Encryption (not hashing) — reversible

**Work factor:** increase as hardware gets faster. Target ~100-300ms per hash.""","security","python","intermediate")

add("what is xss cross site scripting",
"""XSS happens when attackers inject malicious scripts into pages viewed by other users.

**Reflected XSS:**
```
Attacker sends link: https://site.com/search?q=<script>steal(document.cookie)</script>
Server renders: <div>Results for: <script>steal(document.cookie)</script></div>
Victim's browser executes the script!
```

**Prevention:**

**1. Always escape HTML output:**
```python
# Flask/Jinja2 — auto-escapes by default
{{ user_input }}          # safe — escaped
{{ user_input | safe }}   # DANGEROUS — don't use with user data

# Python escape manually
from html import escape
safe_output = escape(user_input)
```

**2. Never use innerHTML with user data:**
```javascript
// DANGEROUS
element.innerHTML = userInput;

// SAFE
element.textContent = userInput;

// If you need HTML — use DOMPurify
import DOMPurify from 'dompurify';
element.innerHTML = DOMPurify.sanitize(userInput);
```

**3. Content Security Policy header:**
```python
response.headers['Content-Security-Policy'] = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'"
)
```

**4. HttpOnly cookies** — prevents JS from reading session cookies:
```python
response.set_cookie('session', token, httponly=True, secure=True, samesite='Strict')
```""","security","general","intermediate")

# ═══════════════════════════════════════════════════════════════════
# MORE PYTHON
# ═══════════════════════════════════════════════════════════════════
add("how to make http requests in python",
"""Use the `requests` library for HTTP in Python.

```python
import requests

# GET request
response = requests.get('https://api.example.com/users')
print(response.status_code)   # 200
print(response.json())         # parsed JSON
print(response.text)           # raw string
print(response.headers)        # response headers

# GET with params
response = requests.get(
    'https://api.example.com/users',
    params={'page': 1, 'limit': 20},  # → ?page=1&limit=20
    headers={'Authorization': 'Bearer token123'}
)

# POST with JSON
response = requests.post(
    'https://api.example.com/users',
    json={'name': 'Alice', 'email': 'a@b.com'},  # auto sets Content-Type
    headers={'Authorization': 'Bearer token123'}
)

# Error handling
response.raise_for_status()  # raises HTTPError if 4xx/5xx

# Session (reuses connections, persists cookies)
with requests.Session() as session:
    session.headers.update({'Authorization': 'Bearer token'})
    users = session.get('/users').json()
    posts = session.get('/posts').json()

# Timeout (always set this!)
response = requests.get(url, timeout=10)  # 10 second timeout

# Async (httpx)
import httpx, asyncio
async def fetch():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.example.com')
        return response.json()
```""","python","python","beginner")

add("what is a python virtual environment",
"""A virtual environment isolates Python packages for each project so they don't conflict.

```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate          # Mac/Linux
venv\\Scripts\\activate             # Windows CMD
venv\\Scripts\\Activate.ps1        # Windows PowerShell

# Install packages (isolated to this env)
pip install flask sqlalchemy pytest

# Save dependencies
pip freeze > requirements.txt

# Install from requirements.txt
pip install -r requirements.txt

# Deactivate
deactivate

# Delete environment
rm -rf venv
```

**Modern alternatives:**

```bash
# uv — extremely fast (Rust-based, recommended 2024+)
pip install uv
uv venv
uv pip install flask

# poetry — dependency management + publishing
pip install poetry
poetry new myproject
poetry add flask
poetry run python app.py

# pipenv — combines pip + venv
pipenv install flask
pipenv shell
```

**Always add to .gitignore:**
```
venv/
.venv/
__pycache__/
*.pyc
.env
```

**Never install packages globally** — always use a virtual environment per project.""","python","python","beginner")

print(f"Generated {len(ALL):,} knowledge entries")

# Save as JSONL (compact)
outfile = OUT / "k001.jsonl"
with open(outfile, 'w', encoding='utf-8') as f:
    for item in ALL:
        f.write(json.dumps(item, separators=(',', ':'), ensure_ascii=False) + '\n')

size = outfile.stat().st_size
print(f"Written: {outfile} ({size/1024:.1f} KB)")

# ═══════════════════════════════════════════════════════════════════
# JAVASCRIPT DEEP
# ═══════════════════════════════════════════════════════════════════
add("what is a promise in javascript",
"""A Promise represents an async operation that will complete (or fail) in the future.

```javascript
// Creating a Promise
const fetchData = new Promise((resolve, reject) => {
  setTimeout(() => {
    if (Math.random() > 0.1) resolve({ data: 'Success!' });
    else reject(new Error('Failed!'));
  }, 1000);
});

// Consuming — .then/.catch
fetchData
  .then(result => console.log(result.data))  // on success
  .catch(err => console.error(err.message))  // on error
  .finally(() => hideSpinner());             // always runs

// Async/await (cleaner syntax — same thing underneath)
async function getData() {
  try {
    const result = await fetchData;          // wait for promise
    return result.data;
  } catch (err) {
    console.error('Error:', err.message);
  }
}

// Parallel execution — run all at once
const [user, posts, comments] = await Promise.all([
  fetch('/api/user').then(r => r.json()),
  fetch('/api/posts').then(r => r.json()),
  fetch('/api/comments').then(r => r.json()),
]);
// Takes max(user, posts, comments) time, not sum

// Promise.race — first one wins
const result = await Promise.race([
  fetch('/api/fast'),
  new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 5000))
]);

// Promise.allSettled — all complete, even if some fail
const results = await Promise.allSettled([req1, req2, req3]);
results.forEach(r => {
  if (r.status === 'fulfilled') use(r.value);
  else log(r.reason);
});
```""","javascript","javascript","intermediate")

add("javascript array methods",
"""Modern JavaScript array methods — master these and you'll write cleaner code.

```javascript
const nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
const users = [
  {name: 'Alice', age: 30, active: true},
  {name: 'Bob', age: 25, active: false},
  {name: 'Charlie', age: 35, active: true},
];

// map — transform each element, returns new array
const doubled = nums.map(n => n * 2);              // [2,4,6,8,10,...]
const names = users.map(u => u.name);              // ['Alice','Bob','Charlie']

// filter — keep elements matching condition
const evens = nums.filter(n => n % 2 === 0);      // [2,4,6,8,10]
const active = users.filter(u => u.active);        // [Alice, Charlie]

// reduce — collapse to single value
const sum = nums.reduce((acc, n) => acc + n, 0);  // 55
const byName = users.reduce((acc, u) => {
  acc[u.name] = u; return acc;
}, {});  // {Alice: {...}, Bob: {...}}

// find / findIndex — first match
const bob = users.find(u => u.name === 'Bob');
const bobIdx = users.findIndex(u => u.name === 'Bob');  // 1

// some / every — boolean checks
const anyMinors = users.some(u => u.age < 18);    // false
const allAdults = users.every(u => u.age >= 18);   // true

// flat / flatMap — flatten nested arrays
const nested = [[1,2], [3,4], [5,6]];
nested.flat();                                      // [1,2,3,4,5,6]
nested.flatMap(arr => arr.map(n => n * 2));        // [2,4,6,8,10,12]

// Chaining
const result = users
  .filter(u => u.active)
  .map(u => u.name)
  .sort();                                          // ['Alice', 'Charlie']

// forEach — side effects (no return value)
users.forEach(u => console.log(u.name));
```""","javascript","javascript","beginner")

add("javascript object methods",
"""Key JavaScript object operations every developer needs.

```javascript
const user = {name: 'Alice', age: 30, city: 'NYC'};

// Access all keys, values, entries
Object.keys(user)    // ['name', 'age', 'city']
Object.values(user)  // ['Alice', 30, 'NYC']
Object.entries(user) // [['name','Alice'], ['age',30], ['city','NYC']]

// Spread — shallow copy and merge
const copy = {...user};
const extended = {...user, role: 'admin'};
const override = {...user, age: 31};  // {name:'Alice', age:31, city:'NYC'}

// Object.assign — same as spread (older syntax)
Object.assign({}, user, {role: 'admin'});

// Destructuring
const {name, age} = user;
const {name: fullName, role = 'user'} = user;  // rename + default

// Check if key exists
'name' in user           // true
user.hasOwnProperty('name')  // true

// Dynamic keys
const key = 'name';
user[key]                // 'Alice'
const obj = {[key]: 'Bob'};  // {name: 'Bob'}

// Object.freeze — prevent modifications
const config = Object.freeze({host: 'localhost', port: 3000});
config.port = 8080;  // silently fails (TypeError in strict mode)

// Convert entries back to object
const pairs = [['a', 1], ['b', 2]];
Object.fromEntries(pairs);  // {a: 1, b: 2}

// Useful pattern — transform object values
const doubled = Object.fromEntries(
  Object.entries({a: 1, b: 2}).map(([k, v]) => [k, v * 2])
);  // {a: 2, b: 4}
```""","javascript","javascript","intermediate")

add("how to handle errors in javascript",
"""Comprehensive error handling in modern JavaScript.

```javascript
// try/catch/finally
try {
  const data = JSON.parse(invalidJson);
} catch (err) {
  if (err instanceof SyntaxError) {
    console.error('Invalid JSON:', err.message);
  } else {
    throw err;  // re-throw unexpected errors
  }
} finally {
  cleanup();   // always runs
}

// Async error handling
async function fetchUser(id) {
  try {
    const resp = await fetch(`/api/users/${id}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  } catch (err) {
    if (err.name === 'TypeError') {
      throw new Error('Network error - check connection');
    }
    throw err;
  }
}

// Custom errors
class ValidationError extends Error {
  constructor(field, message) {
    super(message);
    this.name = 'ValidationError';
    this.field = field;
  }
}

class NotFoundError extends Error {
  constructor(resource) {
    super(`${resource} not found`);
    this.name = 'NotFoundError';
    this.statusCode = 404;
  }
}

// Usage
function validateUser(user) {
  if (!user.email?.includes('@')) {
    throw new ValidationError('email', 'Invalid email format');
  }
}

try {
  validateUser({name: 'Alice'});
} catch (err) {
  if (err instanceof ValidationError) {
    showFieldError(err.field, err.message);
  } else {
    showGenericError();
  }
}

// Global handler (browser)
window.addEventListener('unhandledrejection', event => {
  console.error('Unhandled promise rejection:', event.reason);
  event.preventDefault();
});
```""","javascript","javascript","intermediate")

# ═══════════════════════════════════════════════════════════════════
# REACT DEEP
# ═══════════════════════════════════════════════════════════════════
add("react hooks complete guide",
"""All core React hooks with real examples.

```jsx
import { useState, useEffect, useCallback, useMemo,
         useRef, useContext, useReducer } from 'react';

// useState — local state
const [count, setCount] = useState(0);
const [user, setUser] = useState(null);
setCount(c => c + 1);  // functional update

// useEffect — side effects
useEffect(() => {
  const sub = subscribe(userId);
  return () => sub.unsubscribe();  // cleanup
}, [userId]);  // re-run when userId changes

// useRef — mutable ref, no re-render
const inputRef = useRef(null);
const timerRef = useRef(null);
inputRef.current.focus();
timerRef.current = setTimeout(fn, 1000);

// useMemo — memoize expensive computation
const sortedList = useMemo(() =>
  [...items].sort((a, b) => a.name.localeCompare(b.name)),
  [items]  // only recalculate when items changes
);

// useCallback — memoize function reference
const handleDelete = useCallback((id) => {
  setItems(prev => prev.filter(i => i.id !== id));
}, []);  // stable function — won't cause child re-renders

// useReducer — complex state with actions
const reducer = (state, action) => {
  switch (action.type) {
    case 'INCREMENT': return {...state, count: state.count + 1};
    case 'SET_USER':  return {...state, user: action.payload};
    default: throw Error('Unknown action');
  }
};
const [state, dispatch] = useReducer(reducer, {count: 0, user: null});
dispatch({type: 'SET_USER', payload: {name: 'Alice'}});

// useContext — consume context
const theme = useContext(ThemeContext);

// Custom hook — reuse stateful logic
function useLocalStorage(key, initial) {
  const [value, setValue] = useState(() =>
    JSON.parse(localStorage.getItem(key) ?? JSON.stringify(initial))
  );
  const set = useCallback(v => {
    setValue(v);
    localStorage.setItem(key, JSON.stringify(v));
  }, [key]);
  return [value, set];
}
```""","react","javascript","intermediate")

add("react state management patterns",
"""Choosing the right state management for your React app.

**Local state (useState)** — component-specific, no sharing needed:
```jsx
function Toggle() {
  const [on, setOn] = useState(false);
  return <button onClick={() => setOn(o => !o)}>{on ? 'ON' : 'OFF'}</button>;
}
```

**Lifted state** — shared between sibling components:
```jsx
function Parent() {
  const [value, setValue] = useState('');  // lifted up
  return <>
    <Input value={value} onChange={setValue} />
    <Preview value={value} />
  </>;
}
```

**Context** — deep tree sharing (theme, auth, language):
```jsx
const UserContext = createContext(null);

function App() {
  const [user, setUser] = useState(null);
  return (
    <UserContext.Provider value={{user, setUser}}>
      <Layout />
    </UserContext.Provider>
  );
}
function Avatar() {
  const {user} = useContext(UserContext);  // anywhere in tree
  return <img src={user?.avatar} />;
}
```

**Zustand** — simple global state (recommended for most apps):
```javascript
import { create } from 'zustand';

const useStore = create(set => ({
  count: 0,
  user: null,
  increment: () => set(s => ({count: s.count + 1})),
  setUser: (user) => set({user}),
}));

function Counter() {
  const {count, increment} = useStore();
  return <button onClick={increment}>{count}</button>;
}
```

**Redux Toolkit** — large apps with complex state:
```javascript
const counterSlice = createSlice({
  name: 'counter',
  initialState: {value: 0},
  reducers: {
    increment: state => { state.value += 1; },
    setUser: (state, action) => { state.user = action.payload; }
  }
});
```""","react","javascript","advanced")

# ═══════════════════════════════════════════════════════════════════
# NODE.JS & BACKEND
# ═══════════════════════════════════════════════════════════════════
add("node js event loop explained",
"""Node.js is single-threaded but handles concurrency via the event loop.

```
   ┌─────────────────────────────────┐
   │         Call Stack              │ ← synchronous code runs here
   └─────────────────┬───────────────┘
                     │
   ┌─────────────────▼───────────────┐
   │          Event Loop             │
   └──┬────────────────────────┬─────┘
      │                        │
┌─────▼──────┐          ┌─────▼──────┐
│  Microtask │          │  Macrotask │
│   Queue    │          │   Queue    │
│ (Promises) │          │(setTimeout)│
└────────────┘          └────────────┘
```

```javascript
console.log('1');                     // sync → stack

setTimeout(() => console.log('4'), 0); // macrotask queue

Promise.resolve()
  .then(() => console.log('3'));      // microtask queue

console.log('2');                     // sync → stack

// Output: 1, 2, 3, 4
// Microtasks ALWAYS drain before next macrotask
```

**Phases of event loop:**
1. timers — setTimeout, setInterval callbacks
2. pending callbacks — I/O errors
3. poll — retrieve new I/O events (most I/O callbacks)
4. check — setImmediate callbacks
5. close — cleanup callbacks

**Non-blocking I/O:**
```javascript
// Node delegates I/O to OS, continues running
fs.readFile('big.txt', (err, data) => {
  // This runs when OS says file is ready
  // Meanwhile Node handles other requests
  console.log(data.length);
});
console.log('This runs immediately, before file is read');
```

**libuv** — C library that provides the event loop and thread pool for CPU-intensive work.""","nodejs","javascript","advanced")

add("building rest api with fastapi python",
"""FastAPI is a modern, fast Python web framework with automatic validation and docs.

```python
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Optional
import uvicorn

app = FastAPI(title="My API", version="1.0.0")

# Pydantic models — automatic validation
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    age: int

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True

# Routes
@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/users", response_model=list[UserResponse])
async def get_users(skip: int = 0, limit: int = 20):
    return db.query(User).offset(skip).limit(limit).all()

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user_data: UserCreate):
    user = User(**user_data.dict())
    db.add(user)
    db.commit()
    return user

# Dependency injection
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/items")
async def get_items(db=Depends(get_db)):
    return db.query(Item).all()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
# Auto docs: http://localhost:8000/docs
```""","api","python","intermediate")

# ═══════════════════════════════════════════════════════════════════
# MORE SYSTEM DESIGN
# ═══════════════════════════════════════════════════════════════════
add("how to design a url shortener",
"""Classic system design — URL shortener like bit.ly.

**Requirements:** Shorten URLs, redirect, ~100M URLs, ~10B redirects/day.

**Core algorithm:**
```python
import hashlib, base64, string, random

# Method 1: Base62 encode auto-increment ID
CHARS = string.ascii_letters + string.digits  # 62 chars

def encode(num: int) -> str:
    result = []
    while num:
        result.append(CHARS[num % 62])
        num //= 62
    return ''.join(reversed(result)) or CHARS[0]

encode(1000000)  # '4c92' — 4-7 chars typical

# Method 2: Hash + truncate
def short_code(url: str) -> str:
    h = hashlib.md5(url.encode()).digest()
    return base64.urlsafe_b64encode(h)[:7].decode()
```

**Database schema:**
```sql
CREATE TABLE urls (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    short_code  VARCHAR(10) UNIQUE NOT NULL,
    long_url    TEXT NOT NULL,
    user_id     BIGINT,
    created_at  TIMESTAMP DEFAULT NOW(),
    expires_at  TIMESTAMP,
    click_count BIGINT DEFAULT 0
);
CREATE INDEX idx_short ON urls(short_code);
```

**API:**
```python
# POST /shorten → {short_url: "https://short.ly/abc123"}
# GET /{code}   → 301 redirect to long URL

# Redis cache for hot URLs
cache_key = f"url:{code}"
long_url = redis.get(cache_key)
if not long_url:
    long_url = db.query("SELECT long_url FROM urls WHERE short_code=?", code)
    redis.setex(cache_key, 86400, long_url)  # cache 24h
return redirect(long_url, code=301)
```

**Scale:** 10B redirects/day = ~116K req/sec. Use Redis + read replicas.
**301** = permanent redirect (browser caches, fewer hits).
**302** = temporary redirect (analytics but more server load).""","architecture","general","advanced")

add("explain the solid principles",
"""SOLID are 5 object-oriented design principles for maintainable code.

**S — Single Responsibility:** A class should have one reason to change.
```python
# Bad: one class does everything
class User:
    def save_to_db(self): ...     # DB concern
    def send_email(self): ...      # Email concern
    def validate(self): ...        # Validation concern

# Good: separate concerns
class User: ...
class UserRepository: def save(self, user): ...
class EmailService: def send_welcome(self, user): ...
```

**O — Open/Closed:** Open for extension, closed for modification.
```python
# Bad: modify class to add new shape
class AreaCalculator:
    def area(self, shape):
        if shape.type == 'circle': return 3.14 * shape.r**2
        if shape.type == 'rect': return shape.w * shape.h  # must modify

# Good: extend via polymorphism
class Shape: def area(self): raise NotImplementedError
class Circle(Shape): def area(self): return 3.14 * self.r**2
class Rectangle(Shape): def area(self): return self.w * self.h
# Add Triangle without touching existing code
```

**L — Liskov Substitution:** Subtypes must be substitutable for base types.
**I — Interface Segregation:** Many specific interfaces > one general interface.
**D — Dependency Inversion:** Depend on abstractions, not concretions.

```python
# D — DI example
class EmailService:
    def __init__(self, mailer):  # inject abstraction
        self.mailer = mailer     # could be SMTP, SendGrid, mock

class SMTPMailer: def send(self, to, body): ...
class MockMailer: def send(self, to, body): print(f"Mock: {body}")

service = EmailService(SMTPMailer())   # production
service = EmailService(MockMailer())   # testing
```""","architecture","general","intermediate")

print(f"Total entries now: {len(ALL):,}")

# Overwrite the file with all entries
outfile = OUT / "k001.jsonl"
with open(outfile, 'w', encoding='utf-8') as f:
    for item in ALL:
        f.write(json.dumps(item, separators=(',', ':'), ensure_ascii=False) + '\n')

size = outfile.stat().st_size
print(f"Written: {outfile} ({size/1024:.1f} KB)")
