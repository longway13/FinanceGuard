Below is a structured README snippet that explains how to set up and run your project using nvm and pnpm:

---

```markdown
# FinanceGuard

FinanceGuard is a financial product helper application that leverages RAG-based AI to provide risk analysis and dispute insights for financial products. This guide will help you set up your development environment using **nvm** and **pnpm**.

## Prerequisites

- **nvm (Node Version Manager)**: Ensure you have nvm installed. If not, follow the installation instructions on the [nvm GitHub repository](https://github.com/nvm-sh/nvm).
- **Node.js**: We recommend using the latest version.
- **pnpm**: Our project uses pnpm as its package manager for faster and more efficient dependency management.

## Installation

### 1. Install Node.js with nvm

To install the latest version of Node.js, run:

```bash
nvm install node
```

After installation, verify your Node.js version:

```bash
node -v
```

### 2. Install pnpm

Install pnpm globally by running:

```bash
npm install -g pnpm
```

Verify pnpm installation:

```bash
pnpm -v
```

### 3. Install Project Dependencies

With Node.js and pnpm installed, install the required packages for the project:

```bash
pnpm install
```

## Running the Project

Start the development server with:

```bash
pnpm dev
```


## Troubleshooting

- Ensure you are using the correct Node.js version (use `nvm use <version>` if needed).
- If dependencies fail to install, try clearing the pnpm cache or reinstalling pnpm.
- For further assistance, consult the project documentation or reach out via the issue tracker.

Happy coding!
```

---

This Markdown text clearly explains the required steps, commands, and context for setting up and running your project using nvm and pnpm.
