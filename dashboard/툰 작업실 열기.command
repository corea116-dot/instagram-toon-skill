#!/bin/zsh
set -e
cd -- "$(dirname -- "$0")"
export PATH="${HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:${PATH}"
if /usr/bin/curl -fsS http://localhost:4318/health >/dev/null 2>&1; then
  /usr/bin/open http://localhost:4318
  exit 0
fi
if [[ ! -d node_modules ]]; then npm ci; fi
if [[ ! -f dist/index.html ]]; then npm run build; fi
(
  for attempt in {1..50}; do
    if /usr/bin/curl -fsS http://localhost:4318/health >/dev/null 2>&1; then
      /usr/bin/open http://localhost:4318
      break
    fi
    sleep 0.2
  done
) &
npm start
