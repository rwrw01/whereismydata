import { execSync } from "node:child_process";

const COMPOSE_PATH =
  process.env.HAR_PROVIDER_LOOKUP_COMPOSE_PATH ?? "../api/docker-compose.yml";

export default function globalSetup(): void {
  execSync(`docker compose -f ${COMPOSE_PATH} up -d --build --wait`, {
    stdio: "inherit",
    env: { ...process.env, ALLOWED_ORIGIN: "http://localhost:4173" },
  });
}
