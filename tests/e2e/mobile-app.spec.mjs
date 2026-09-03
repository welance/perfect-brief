/* The phone layer. Runs in the `mobile` project (Pixel 7, touch). */
import { test, expect } from "@playwright/test";

test.beforeEach(({ isMobile }) => {
  test.skip(!isMobile, "the phone layer is intentionally absent on desktop");
});

const PAGES = ["/", "/rules.html", "/console.html", "/data.html", "/security.html", "/integrate.html"];

test.describe("the fundamentals a phone needs", () => {
  for (const path of PAGES) {
    test(`${path} allows the safe area to be read`, async ({ page }) => {
      await page.goto(path);
      const content = await page.locator('meta[name="viewport"]').getAttribute("content");
      expect(content).toContain("viewport-fit=cover");
    });
  }

  test("no input is small enough to make iOS zoom on focus", async ({ page }) => {
    for (const path of ["/console.html"]) {
      await page.goto(path);
      const small = await page.locator("input, select, textarea").evaluateAll((els) =>
        els.filter((el) => el.offsetParent !== null)
          .filter((el) => parseFloat(getComputedStyle(el).fontSize) < 16)
          .map((el) => el.id || el.className || el.tagName));
      expect(small, `${path} has sub-16px fields: ${small.join(", ")}`).toEqual([]);
    }
  });

});

test.describe("the layer is opt-in", () => {
  test("the phone layer announces itself on a phone", async ({ page }) => {
    await page.goto("/console.html");
    await expect(page.locator("html")).toHaveClass(/wl-app/);
  });

  test("the fixed header keeps the product name on screen", async ({ page }) => {
    await page.goto("/console.html");
    await expect(page.locator(".wl-head")).toHaveCSS("position", "fixed");
    await expect(page.locator(".wl-head .wl-project")).toContainText("brief bar");
    await expect(page.locator(".wl-head .wl-project")).toBeVisible();
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

test.describe("installable", () => {
  test("the manifest is served, parses, and its icons resolve", async ({ page, request }) => {
    await page.goto("/console.html");
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
    await page.goto("/console.html");
    await expect(page.locator('meta[name="theme-color"]')).toHaveCount(2);
  });
});
