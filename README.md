

# FinanceGuard

FinanceGuard is an AI-powered financial product helper application designed to support secure financial activities by analyzing hidden risks in finance contracts and providing dispute insights.

## Features

- **Risk Analysis:** Upload your financial contract and let our AI agent detect hidden risks.
- **Future Risk Simulation:** Predict potential future risks and review historical dispute cases.
- **Highlighted Risk Elements:** Key risk elements related to your queries are highlighted in contract PDFs.

## Technologies Used

- **AI Tools:** Langraph, Langchain, Upstage Document_parse, Tavily, Kure (Embedding Model)
- **Frontend:** React.js, Next.js

## Prerequisites

### Frontend Setup

- **nvm (Node Version Manager):** Ensure you have nvm installed. For installation instructions, refer to the [nvm GitHub repository](https://github.com/nvm-sh/nvm).
- **Node.js:** It is recommended to use the latest version.
- **pnpm:** We use pnpm for faster and more efficient dependency management.

## Installation and Running

### 1. Install Node.js Using nvm

To install the latest version of Node.js, run:
```bash
nvm install node
```
After installation, verify your Node.js version:
```bash
node -v
```

### 2. Install pnpm Globally

Install pnpm globally using npm:
```bash
npm install -g pnpm
```
Verify the installation:
```bash
pnpm -v
```

### 3. Install Project Dependencies

In the frontend directory, install the required packages:
```bash
pnpm install
```

### 4. Run the Frontend Server

Start the development server:
```bash
pnpm dev
```

## Run the Backend Server

From the project root directory, start the backend server:
```bash
python backend/app.py
```
