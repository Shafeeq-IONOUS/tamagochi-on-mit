// Print every mascot's 5x5 sprite (next to its 9x9 original, for comparison) as a colored block
// map in the terminal — a quick eyeball check for new pixel art with no sim instance, no
// credentials, and no network access needed.
//
//   node scripts/preview-mascots-5x5.js
import { MASCOTS } from "../src/sprites.js";

const RESET = "\x1b[0m";
const block = (rgb) => (rgb ? `\x1b[48;2;${rgb[0]};${rgb[1]};${rgb[2]}m  ${RESET}` : "  ");

function gridLines(sprite, colors) {
  return sprite.map((row) => [...row].map((ch) => block(ch === "." ? null : colors[ch])).join(""));
}

function printSideBySide(leftLines, rightLines, gap = "    ") {
  const height = Math.max(leftLines.length, rightLines.length);
  for (let i = 0; i < height; i++) {
    const left = leftLines[i] ?? "";
    console.log(`${left}${gap}${rightLines[i] ?? ""}`);
  }
}

for (const [id, m] of Object.entries(MASCOTS)) {
  console.log(`\n${m.name} (${id}${m.school ? `, ${m.school}` : ", no school"})`);
  console.log(`9x9 idle${" ".repeat(9 * 2 - "9x9 idle".length + 4)}5x5 idle    5x5 blink   5x5 eat`);
  const nine = gridLines(m.sprite, m.colors);
  if (!m.sprite5) {
    console.log("(no sprite5 yet)");
    continue;
  }
  const idle5 = gridLines(m.poses5.idle, m.colors);
  const blink5 = gridLines(m.poses5.blink, m.colors);
  const eat5 = gridLines(m.poses5.eat, m.colors);
  const height = Math.max(nine.length, idle5.length, blink5.length, eat5.length);
  for (let i = 0; i < height; i++) {
    const cells = [nine[i], idle5[i], blink5[i], eat5[i]].map((l) => l ?? "");
    console.log(cells.join("   "));
  }
  console.log(`  raw 5x5 rows: ${JSON.stringify(m.sprite5)}`);
}
console.log("\n(if your terminal doesn't support 24-bit color, the blocks above will look wrong —\n the raw row strings printed under each mascot are the ground truth.)");
