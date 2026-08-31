/* The phone layer. Runs in the `mobile` project (Pixel 7, touch). */
import { test, expect } from "@playwright/test";

test.beforeEach(({ isMobile }) => {
  test.skip(!isMobile, "the phone layer is intentionally absent on desktop");
});

const PAGES = ["/", "/rules.html", "/console.html", "/data.html", "/security.html",
  "/integrate.html", "/calculators.html", "/price.html", "/team.html"];

async function dragY(page, from, to, steps = 12) {
  await page.evaluate(async ({ from, to, steps }) => {
    const target = document.elementFromPoint(from.x, from.y);
    const fire = (type, x, y) => target.dispatchEvent(new PointerEvent(type, {
      bubbles: true, cancelable: true, pointerId: 7, pointerType: "touch", clientX: x, clientY: y,
    }));
    fire("pointerdown", from.x, from.y);
    for (let i = 1; i <= steps; i++) {
      fire("pointermove", from.x, from.y + ((to.y - from.y) * i) / steps);
      await new Promise((resolve) => setTimeout(resolve, 2));
    }
    fire("pointerup", to.x, to.y);
  }, { from, to, steps });
}

async function dragX(target, dx, steps = 10) {
  await target.evaluate(async (el, { dx, steps }) => {
    const rect = el.getBoundingClientRect();
    const from = { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
    const fire = (type, x) => el.dispatchEvent(new PointerEvent(type, {
      bubbles: true, cancelable: true, pointerId: 8, pointerType: "touch", clientX: x, clientY: from.y,
    }));
    fire("pointerdown", from.x);
    for (let i = 1; i <= steps; i++) {
      fire("pointermove", from.x + (dx * i) / steps);
      await new Promise((resolve) => setTimeout(resolve, 2));
    }
    fire("pointerup", from.x + dx);
  }, { dx, steps });
}

test.describe("the fundamentals a phone needs", () => {
  for (const path of PAGES) {
    test(`${path} allows the safe area to be read`, async ({ page }) => {
      await page.goto(path);
      const content = await page.locator('meta[name="viewport"]').getAttribute("content");
      expect(content).toContain("viewport-fit=cover");
    });
  }

  test("no input is small enough to make iOS zoom on focus", async ({ page }) => {
    for (const path of ["/price.html", "/team.html", "/console.html"]) {
      await page.goto(path);
      const small = await page.locator("input, select, textarea").evaluateAll((els) =>
        els.filter((el) => el.offsetParent !== null)
          .filter((el) => parseFloat(getComputedStyle(el).fontSize) < 16)
          .map((el) => el.id || el.className || el.tagName));
      expect(small, `${path} has sub-16px fields: ${small.join(", ")}`).toEqual([]);
    }
  });

  test("every number field asks for the numeric keyboard", async ({ page }) => {
    for (const path of ["/price.html", "/team.html"]) {
      await page.goto(path);
      const missing = await page.locator('input[type="number"]').evaluateAll((els) =>
        els.filter((el) => el.getAttribute("inputmode") !== "decimal").map((el) => el.id));
      expect(missing, `${path} number fields without inputmode`).toEqual([]);
    }
  });
});

test.describe("the layer is opt-in", () => {
  test("the phone layer announces itself on a phone", async ({ page }) => {
    await page.goto("/price.html");
    await expect(page.locator("html")).toHaveClass(/wl-app/);
  });

  test("the fixed header keeps the product name on screen", async ({ page }) => {
    await page.goto("/price.html");
    await expect(page.locator(".wl-head")).toHaveCSS("position", "sticky");
    await expect(page.locator(".wl-head .wl-project")).toContainText("brief bar");
    await expect(page.locator(".wl-head .wl-project")).toBeVisible();
  });
});

test.describe("the calculator workspace", () => {
  test("edits one useful section at a time", async ({ page }) => {
    await page.goto("/price.html");
    const sections = page.locator(".wl-calc-inputs > section.card");
    await expect(sections.first()).toBeVisible();
    await expect(sections.nth(1)).toBeHidden();
    await expect(page.locator(".wl-calc-count")).toContainText("1");
    await page.locator(".wl-calc-nav button").last().click();
    await expect(sections.first()).toBeHidden();
    await expect(sections.nth(1)).toBeVisible();
    await expect(page.locator(".wl-calc-count")).toContainText("2");
  });

  test("switches explicitly to a compact answer", async ({ page }) => {
    await page.goto("/price.html");
    await page.locator(".wl-calc-modes button").last().click();
    await expect(page.locator(".wl-calc-answer")).toBeVisible();
    await expect(page.locator(".wl-calc-inputs")).toBeHidden();
    await expect(page.locator(".wl-calc-details")).not.toHaveAttribute("open", "");
    await expect(page.locator(".wl-calc-answer")).not.toHaveClass(/wl-sheet/);
  });

  test("the page ends above the fixed answer footer", async ({ page }) => {
    await page.goto("/price.html");
    const pad = await page.evaluate(() => parseFloat(getComputedStyle(document.body).paddingBottom));
    const footer = await page.locator(".wl-answer-footer").evaluate((el) => el.offsetHeight);
    expect(pad).toBeGreaterThan(footer);
  });
});

test.describe("the fixed answer summary", () => {
  test("shows the answer without opening anything", async ({ page }) => {
    await page.goto("/price.html");
    const footer = page.locator(".wl-answer-footer");
    await expect(footer).toBeVisible();
    await expect(footer.locator(".wl-answer-v")).not.toHaveText("—");
    await expect(footer.locator(".wl-answer-bar i")).toHaveCount(3);
    await expect(footer).toBeInViewport();
  });

  test("follows the figures as you change the inputs", async ({ page }) => {
    await page.goto("/price.html");
    const v = page.locator(".wl-answer-v");
    const before = await v.textContent();
    await page.fill("#rate", "250");
    await page.locator("#rate").blur();
    await expect(v).not.toHaveText(before);
    await expect(v).toHaveText(await page.locator("#figPay").textContent());
  });

  test("opens the answer when tapped", async ({ page }) => {
    await page.goto("/team.html");
    await page.locator(".wl-answer-footer").click();
    await expect(page.locator(".wl-calc-modes button").last()).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator(".wl-calc-answer")).toBeVisible();
  });
});

test.describe("the console's verdict", () => {
  test("still toggles by tap, and now also by drag", async ({ page }) => {
    await page.goto("/console.html");
    const v = page.locator("#vstick");
    await expect(v).toHaveClass(/wl-sheet/);
    await expect(v).toHaveClass(/collapsed/);
    await page.locator("#vhandle").click();
    await page.waitForTimeout(450);
    await expect(v).not.toHaveClass(/collapsed/);
    await expect(page.locator(".track-wrap")).toBeInViewport();
  });
});

test.describe("swiping a role away", () => {
  test("reveals delete, and asks before it removes", async ({ page }) => {
    await page.goto("/team.html");
    await page.waitForTimeout(450);
    const rows = page.locator("#rows .role");
    const n = await rows.count();
    await rows.first().evaluate((el) => el.scrollIntoView({ block: "center" }));
    await dragX(rows.first(), -110);
    await page.waitForTimeout(400);
    await expect(page.locator(".wl-swipe-act.is-live")).toBeVisible();
    await expect(rows).toHaveCount(n);
    await page.locator(".wl-swipe-del").click();
    await page.waitForTimeout(400);
    await expect(rows).toHaveCount(n - 1);
  });

  test("a vertical drag scrolls and never opens the action", async ({ page }) => {
    await page.goto("/team.html");
    await page.locator("#rows .role").first().evaluate((el) => el.scrollIntoView({ block: "center" }));
    const box = await page.locator("#rows .role").first().boundingBox();
    await dragY(page, { x: box.x + box.width / 2, y: box.y + box.height / 2 },
      { x: box.x + box.width / 2, y: box.y - 150 });
    await page.waitForTimeout(300);
    await expect(page.locator(".wl-swipe-act.is-live")).toHaveCount(0);
  });
});

test.describe("installable", () => {
  test("the manifest is served, parses, and its icons resolve", async ({ page, request }) => {
    await page.goto("/price.html");
    const href = await page.locator('link[rel="manifest"]').getAttribute("href");
    expect(href).toBe("/manifest.webmanifest");
    const res = await request.get(href);
    expect(res.status()).toBe(200);
    const m = await res.json();
    expect(m.display).toBe("standalone");
    expect(m.icons.length).toBeGreaterThanOrEqual(3);
    for (const icon of m.icons) expect((await request.get(icon.src)).status()).toBe(200);
  });

  test("both themes declare a colour for the browser chrome", async ({ page }) => {
    await page.goto("/price.html");
    await expect(page.locator('meta[name="theme-color"]')).toHaveCount(2);
  });
});
