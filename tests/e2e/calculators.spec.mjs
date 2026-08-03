/* The calculators, driven like a person would.
 *
 * The engine's own numbers are pinned in tests/site/pricing.test.mjs; here we
 * check that the UI actually shows them — the wiring, the persistence, and
 * the two promises the model makes visually: the bands always sum, and a
 * no-deal is never quietly absorbed.
 */
import { test, expect } from "@playwright/test";

const eur = (s) => Number(String(s).replace(/[^\d.,-]/g, "").replace(",", "."));

test.describe("perfect price", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/price.html");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  test("defaults show the worked case: 50% coverage → WITH SUPPORT → €50 of €100", async ({ page }) => {
    await expect(page.locator("#levelname")).toHaveText("WITH SUPPORT");
    await expect(page.locator("#covpct")).toHaveText("50%");
    await expect(page.locator("#figShare")).toHaveText("50%");
    await expect(page.locator("#figMargin")).toHaveText("50%");
    await expect(page.locator("#figPay")).toContainText("50.00");
  });

  test("covering every part fully walks up to AUTONOMOUS 70/30", async ({ page }) => {
    for (const sel of await page.locator("#rows .comp select").all()) {
      await sel.selectOption("1");
    }
    await expect(page.locator("#levelname")).toHaveText("AUTONOMOUS");
    await expect(page.locator("#figShare")).toHaveText("70%");
    await expect(page.locator("#figMargin")).toHaveText("30%");
  });

  test("the cost-of-living floor binds, and the differential stays its own band", async ({ page }) => {
    await page.locator("#usegeo").check();
    // defaults: WITH SUPPORT (share 50%) → €50 role-only; Pakistan 0.28 with a
    // 0.5 floor → the floor wins, so €50 × 0.5 = €25
    await expect(page.locator("#figPay")).toContainText("25.00");
    const geo = page.locator("#barGeo");
    await expect(geo).toBeVisible();
    await expect
      .poll(() => geo.evaluate((el) => el.getBoundingClientRect().width), { timeout: 2000 })
      .toBeGreaterThan(1); // its own band — never folded into margin
    // the note always states role-only pay next to local pay — the differential
    // is spelled out, never inferred
    await expect(page.locator("#geonote")).toContainText("50.00");
    await expect(page.locator("#geonote")).toContainText("25.00");
  });

  test("edits survive a reload, reset restores the defaults", async ({ page }) => {
    const first = page.locator("#rows .comp input[type=text]").first();
    await first.fill("EDITED PART");
    await page.reload();
    await expect(page.locator("#rows .comp input[type=text]").first()).toHaveValue("EDITED PART");
    await page.locator("#reset").click();
    await expect(page.locator("#rows .comp input[type=text]").first()).toHaveValue("CraftCMS");
  });

  test("internal work: no margin — what is not covered alone is welance support", async ({ page }) => {
    await page.locator("#w-internal").click();

    // full autonomy: the person keeps the whole cap, support is zero
    await expect(page.locator("#figShare")).toHaveText("100%");
    await expect(page.locator("#t-f-margin")).toHaveText("welance support");
    await expect(page.locator("#figMargin")).toHaveText("0%");
    await expect(page.locator("#figPay")).toContainText("50.00");
    await expect(page.locator("#formula")).not.toContainText("70%");

    // drop both views (a one-step gap rounds toward the person, §4): the
    // uncovered part becomes a colleague's real time, and the rate follows
    for (const sel of await page.locator("#rows .comp select").all()) {
      await sel.selectOption("0.5");
    }
    await expect(page.locator("#levelname")).toHaveText("WITH SUPPORT");
    await expect(page.locator("#figShare")).toHaveText("71%");
    await expect(page.locator("#figMargin")).toHaveText("29%");
    await expect(page.locator("#splitkey")).toContainText("welance support");
    await expect(page.locator("#figPay")).toContainText("35.71");

    // the two bands fill the bar: nothing hides
    const w = await page.evaluate(() => {
      const bar = document.querySelector(".splitbar").getBoundingClientRect().width;
      const sum = ["barPerson", "barGeo", "barCompany"].reduce(
        (t, id) => t + document.getElementById(id).getBoundingClientRect().width, 0);
      return { bar, sum };
    });
    expect(Math.abs(w.sum - w.bar)).toBeLessThan(4);
  });
});

test.describe("perfect team", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/team.html?lang=en");
    await page.evaluate(() => localStorage.removeItem("welance-team-calc-v1"));
    await page.reload();
  });

  test("the default team shows the pinned decomposition", async ({ page }) => {
    await expect(page.locator("#figPeople")).toContainText("37.50");
    await expect(page.locator("#figMinR")).toContainText("81.30");
    await expect(page.locator("#formula")).toContainText("9.64");
    await expect(page.locator("#formula")).toContainText("13.36");
    await expect(page.locator("#formula")).toContainText("39.50");
    await expect(page.locator("#verdict .verdict")).toHaveClass(/ok/);
  });

  test("the four bands fill the whole bar — the equation, visually", async ({ page }) => {
    const widths = await page.evaluate(() => {
      const ids = ["barPeople", "barHead", "barGeo", "barCompany"];
      const bar = document.querySelector(".splitbar").getBoundingClientRect().width;
      const sum = ids.reduce(
        (t, id) => t + document.getElementById(id).getBoundingClientRect().width, 0);
      return { bar, sum };
    });
    expect(Math.abs(widths.sum - widths.bar)).toBeLessThan(4); // sub-pixel flex rounding
  });

  test("below the minimum viable rate, the flagged role says so and no equation is shown", async ({ page }) => {
    await page.locator("#rate").fill("70");
    await expect(page.locator("#verdict .verdict")).toHaveClass(/no/);
    await expect(page.locator("#rows .rowflag").first()).toBeVisible();
    await expect(page.locator(".ceil.bad").first()).toBeVisible();
    await expect(page.locator("#formula")).toContainText("no-deal");
  });

  test("the first check is derived from project size, not chosen twice", async ({ page }) => {
    await expect(page.locator("#checkval")).toHaveText("2 weeks");
    await page.locator("#projsize").selectOption("s");
    await expect(page.locator("#checkval")).toHaveText("3 days");
    await page.locator("#projsize").selectOption("l");
    await expect(page.locator("#checkval")).toHaveText("1 month");
    await expect(page.locator("#firstcheck")).toHaveCount(0); // no second knob
  });

  test("the cost-of-living floor is a sentence, and it moves the numbers", async ({ page }) => {
    const floor = page.locator("#floorc");
    await expect(floor).toContainText("no floor");
    const geoWidth = () => page.locator("#barGeo").evaluate((el) => el.getBoundingClientRect().width);
    expect(await geoWidth()).toBeGreaterThan(1); // a real differential with no floor
    await floor.selectOption("1"); // full role pay — geography off
    // the bar animates (250ms) — poll rather than catch it mid-transition
    await expect.poll(geoWidth, { timeout: 2000 }).toBeLessThan(1);
    await expect(page.locator("#formula")).not.toContainText("13.36");
  });

  // The shares are a split of one project, so 100% is not a rule the reader
  // has to keep — it is a property no gesture is allowed to break.
  const shares = (page) =>
    page.$$eval("#rows .sharecell input", (els) => els.map((e) => Number(e.value)));
  const total = async (page) => (await shares(page)).reduce((a, b) => a + b, 0);

  test("adding and removing a role still describes one whole project", async ({ page }) => {
    expect(await total(page)).toBe(100);
    await page.locator("#add").click();
    await expect(page.locator("#rows .role")).toHaveCount(4);
    expect(await total(page), "a new role must take its share from the others").toBe(100);
    await page.locator("#rows .role .iconbtn").last().click();
    await expect(page.locator("#rows .role")).toHaveCount(3);
    expect(await total(page), "a removed role gives its share back").toBe(100);
    // the last role standing owns the whole project, and cannot be removed
    for (let i = 0; i < 5; i++) await page.locator("#rows .role .iconbtn").last().click();
    await expect(page.locator("#rows .role")).toHaveCount(1);
    expect(await shares(page)).toEqual([100]);
  });

  test("dragging a boundary moves effort between two roles, never out of the project", async ({ page }) => {
    await page.locator("#effortbar").scrollIntoViewIfNeeded();
    const bar = await page.locator("#effortbar").boundingBox();
    const grip = await page.locator(".grip").first().boundingBox();
    const y = grip.y + grip.height / 2;

    await page.mouse.move(grip.x + grip.width / 2, y);
    await page.mouse.down();
    await page.mouse.move(bar.x + bar.width * 0.6, y, { steps: 10 });
    await page.mouse.up();

    const after = await shares(page);
    expect(after[0], "the first role grew").toBeGreaterThan(30);
    expect(after[2], "the role beyond the boundary was left alone").toBe(25);
    expect(await total(page)).toBe(100);

    // dragged past the edge: a share stops at nothing, it never goes negative
    const g2 = await page.locator(".grip").first().boundingBox();
    await page.mouse.move(g2.x + g2.width / 2, y);
    await page.mouse.down();
    await page.mouse.move(bar.x - 500, y, { steps: 8 });
    await page.mouse.up();
    expect((await shares(page))[0]).toBe(0);
    expect(await total(page)).toBe(100);
  });

  test("the boundary answers the keyboard too", async ({ page }) => {
    const grip = page.locator(".grip").first();
    await grip.focus();
    await expect(grip).toHaveAttribute("role", "slider");
    await grip.press("ArrowRight");
    expect(await shares(page)).toEqual([31, 44, 25]);
    await grip.press("Shift+ArrowRight");
    expect(await shares(page)).toEqual([41, 34, 25]);
    expect(await total(page)).toBe(100);
  });

  test("typing a share makes room in the others", async ({ page }) => {
    await page.locator("#rows .sharecell input").first().fill("60");
    expect(await total(page)).toBe(100);
    expect((await shares(page))[0]).toBe(60);
  });
});
