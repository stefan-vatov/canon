// Fails the build when public/llms.txt carries a stale "Last verified" stamp.
// The stamp is a claim that every fact on the page was checked on that date,
// so it must never be auto-bumped — re-verify the facts, then update the date.
import { readFileSync } from "node:fs";

const MAX_AGE_DAYS = 90;

const page = readFileSync(new URL("../public/llms.txt", import.meta.url), "utf8");
const match = page.match(/^Last verified: (\d{4}-\d{2}-\d{2})/m);

if (!match) {
  console.error("llms.txt: missing 'Last verified: YYYY-MM-DD' stamp");
  process.exit(1);
}

const ageDays = (Date.now() - Date.parse(`${match[1]}T00:00:00Z`)) / 86_400_000;

if (Number.isNaN(ageDays) || ageDays < 0) {
  console.error(`llms.txt: 'Last verified' date ${match[1]} is invalid or in the future`);
  process.exit(1);
}
if (ageDays > MAX_AGE_DAYS) {
  console.error(
    `llms.txt: 'Last verified' stamp is ${Math.floor(ageDays)} days old (max ${MAX_AGE_DAYS}).`,
    "Re-verify the page's facts against the repository, then update the date.",
  );
  process.exit(1);
}

console.log(`llms.txt freshness ok: last verified ${match[1]} (${Math.floor(ageDays)} days ago)`);
