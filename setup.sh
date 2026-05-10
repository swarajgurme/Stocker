#!/bin/bash
# Stocker Enterprise - Setup Script
# Installs dependencies, initializes database, and starts services

set -e

echo "=========================================="
echo "Stocker Enterprise AI Platform Setup"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# --------------------------------------------
# 1. Environment Setup
# --------------------------------------------
echo -e "${YELLOW}[1/7] Setting up environment...${NC}"

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created from template${NC}"
    echo -e "${YELLOW}⚠  Edit .env to configure database credentials${NC}"
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

# --------------------------------------------
# 2. Backend Dependencies
# --------------------------------------------
echo -e "${YELLOW}[2/7] Installing Python dependencies...${NC}"
cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

source venv/bin/activate
pip install --upgrade pip > /dev/null
pip install -r requirements.txt 2>&1 | grep -v "already satisfied" || true
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# --------------------------------------------
# 3. Create logs directory
# --------------------------------------------
mkdir -p logs
touch logs/app.log
echo -e "${GREEN}✓ Logs directory ready${NC}"

# --------------------------------------------
# 4. Initialize Database
# --------------------------------------------
echo -e "${YELLOW}[4/7] Initializing database...${NC}"
python scripts/init_db.py || {
    echo -e "${RED}✗ Database initialization failed${NC}"
    echo "Make sure PostgreSQL is running and DATABASE_URL is correct"
    exit 1
}
echo -e "${GREEN}✓ Database initialized${NC}"

# --------------------------------------------
# 5. Frontend Dependencies
# --------------------------------------------
echo -e "${YELLOW}[5/7] Installing Node dependencies...${NC}"
cd ../frontend
if [ ! -d "node_modules" ]; then
    npm install
    echo -e "${GREEN}✓ Node modules installed${NC}"
else
    echo -e "${GREEN}✓ Node modules already installed${NC}"
fi
cd ..

# --------------------------------------------
# 6. Start Services (Docker or local)
# --------------------------------------------
echo -e "${YELLOW}[6/7] Starting services...${NC}"

if command -v docker-compose &> /dev/null && [ -f "docker-compose.yml" ]; then
    echo "Using Docker Compose..."
    docker-compose up -d postgres redis
    echo -e "${GREEN}✓ Database and Redis started${NC}"
else
    echo -e "${YELLOW}⚠ Docker not found. Starting services manually.${NC}"
    echo "Ensure PostgreSQL is running on localhost:5432"
    echo "Ensure Redis is running on localhost:6379"
fi

# --------------------------------------------
# 7. Run Migrations (if using local DB)
# --------------------------------------------
echo -e "${YELLOW}[7/7] Running final checks...${NC}"
cd backend
source venv/bin/activate
python -c "
from database import check_db_connection
if check_db_connection():
    print('Database connection: OK')
else:
    print('Database connection: FAILED')
    exit(1)
"
echo -e "${GREEN}✓ All checks passed${NC}"

# --------------------------------------------
# Completion
# --------------------------------------------
echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file if needed (database credentials, etc.)"
echo "2. Start the backend: cd backend && python server_new.py"
echo "3. In another terminal, start frontend: cd frontend && npm run dev"
echo ""
echo "Access the application:"
echo "  Frontend: http://localhost:5173"
echo "  Backend API: http://localhost:5000"
echo "  Health Check: http://localhost:5000/health"
echo ""
echo "Default login:"
echo "  Email: admin@stocker.com"
echo "  Password: Admin@123"
echo ""
