module.exports = {
  apps: [
    {
      name: "nextjs",
      cwd: "frontend",
      script: "node_modules/next/dist/bin/next",
      args: "dev -H 0.0.0.0 -p 3000",
      exec_mode: "fork",
      watch: false,    
      autorestart: false,
      exp_backoff_restart_delay: 100,
      max_restarts: 10,
      disable_metrics: true,
      env: {
        "NODE_ENV": "development"
      },
      node_args: [],
    },
    {
      name: "fastapi",
      cwd: "backend",
      script: "uvicorn",
      args: "main:app --host=0.0.0.0 --port=8000", // --reload 없음
      watch: true, // 모든 파일 감시
      ignore_watch: ["backend/logs", "backend/__pycache__", "backend/**/*.pyc", "backend/Log", "backend/moca"],
      autorestart: true,
      disable_metrics: true,
      env: {
        "SKIP_CAMERA": "true",
        "LOG_LEVEL": "ERROR"
      }
    }
  ]
};
