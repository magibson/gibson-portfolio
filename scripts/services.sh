#!/usr/bin/env bash
set -euo pipefail

# Simple, colorful service manager for JARVIS apps

RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
BOLD="\033[1m"
DIM="\033[2m"
NC="\033[0m"

# service -> port
SERVICES=(
  "jarvis-dashboard.service"
  "jarvis-stock.service"
  "jarvis-leads.service"
  "jarvis-callprep.service"
  "jarvis-health.service"
  "jarvis-moveout.service"
  "jarvis-portfolio.service"
)

declare -A PORTS=(
  ["jarvis-dashboard.service"]=8080
  ["jarvis-stock.service"]=8084
  ["jarvis-leads.service"]=8081
  ["jarvis-callprep.service"]=8082
  ["jarvis-health.service"]=8087
  ["jarvis-moveout.service"]=8088
  ["jarvis-portfolio.service"]=8089
)

declare -A ALIASES=(
  ["dashboard"]="jarvis-dashboard.service"
  ["stock"]="jarvis-stock.service"
  ["leads"]="jarvis-leads.service"
  ["callprep"]="jarvis-callprep.service"
  ["call-prep"]="jarvis-callprep.service"
  ["health"]="jarvis-health.service"
  ["moveout"]="jarvis-moveout.service"
  ["move-out"]="jarvis-moveout.service"
  ["portfolio"]="jarvis-portfolio.service"
  ["photo"]="jarvis-portfolio.service"
)

usage() {
  cat <<USAGE
Usage: services.sh <status|start|stop|restart|logs> [name]

Commands:
  status            Show all jarvis services and ports
  start [name]      Start one service or all
  stop [name]       Stop one service or all
  restart [name]    Restart one service or all
  logs [name]       Show recent logs (default: all)

Names:
  dashboard | stock | leads | callprep | call-prep | full service name
USAGE
}

resolve_service() {
  local name="${1:-}"
  if [[ -z "$name" || "$name" == "all" ]]; then
    return 1
  fi
  if [[ -n "${ALIASES[$name]+x}" ]]; then
    printf '%s' "${ALIASES[$name]}"
    return 0
  fi
  if [[ "$name" == *.service ]]; then
    printf '%s' "$name"
    return 0
  fi
  return 2
}

status_one() {
  local svc="$1"
  local port="${PORTS[$svc]:-?}"
  local state
  state="$(systemctl --user is-active "$svc" 2>/dev/null || true)"

  local label color
  case "$state" in
    active)
      label="ACTIVE"; color="$GREEN" ;;
    inactive)
      label="INACTIVE"; color="$DIM" ;;
    failed)
      label="FAILED"; color="$RED" ;;
    *)
      label="${state:-UNKNOWN}"; color="$YELLOW" ;;
  esac

  printf "%b%-28s%b port %b%-5s%b %b[%s]%b\n" \
    "$BOLD" "$svc" "$NC" \
    "$BLUE" "$port" "$NC" \
    "$color" "$label" "$NC"
}

status_all() {
  echo -e "${BOLD}JARVIS Services${NC}"
  for svc in "${SERVICES[@]}"; do
    status_one "$svc"
  done
}

run_all() {
  local action="$1"
  for svc in "${SERVICES[@]}"; do
    systemctl --user "$action" "$svc"
  done
}

run_one() {
  local action="$1" svc="$2"
  systemctl --user "$action" "$svc"
}

logs_one() {
  local svc="$1"
  echo -e "${BOLD}${svc}${NC}"
  journalctl --user -u "$svc" -n 100 --no-pager
}

logs_all() {
  for svc in "${SERVICES[@]}"; do
    logs_one "$svc"
    echo ""
  done
}

main() {
  local cmd="${1:-}"
  local name="${2:-}"

  case "$cmd" in
    status)
      status_all
      ;;
    start|stop|restart)
      if svc="$(resolve_service "$name")"; then
        run_one "$cmd" "$svc"
      else
        run_all "$cmd"
      fi
      ;;
    logs)
      if svc="$(resolve_service "$name")"; then
        logs_one "$svc"
      else
        logs_all
      fi
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      echo -e "${RED}Unknown command:${NC} $cmd"
      usage
      exit 1
      ;;
  esac
}

main "$@"
