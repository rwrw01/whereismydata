import { execSync } from "node:child_process";

const COMPOSE_PATH =
  process.env.HAR_PROVIDER_LOOKUP_COMPOSE_PATH ?? "../api/docker-compose.yml";

export default function globalTeardown(): void {
  execSync(`docker compose -f ${COMPOSE_PATH} down`, {
    stdio: "inherit",
  });
}
