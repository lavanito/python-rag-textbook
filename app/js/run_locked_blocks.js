// Prints, as JSON, the locked block for each case, so tests/test_locked_block_js.py
// can compare with Python and with app/data/bank_replies.json.
// Usage: node app/js/run_locked_blocks.js app/data/figures.json cases.json
// cases.json: [{"question": ..., "parameters": {...}, "class": ... or null}, ...]
const fs = require("fs");
const { lockedBlock, reply } = require("./locked_block.js");

const figures = JSON.parse(fs.readFileSync(process.argv[2], "utf-8"));
const cases = JSON.parse(fs.readFileSync(process.argv[3], "utf-8"));
const out = cases.map((c) => ({
  block: lockedBlock(figures, c.question, c.parameters),
  reply: reply(figures, c.question, c.parameters, c.class),
}));
process.stdout.write(JSON.stringify(out));
