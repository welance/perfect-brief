/* The public surface: one origin, eight languages, no dead ends.
 *
 * These are the promises a visitor and a forker both rely on — the pages and
 * the API live together, every page carries the same chrome, the language
 * follows you, and nothing on the site reaches for an external host.
 */
import { test, expect } from "@playwright/test";

const PAGES = ["/", "/method.html", "/price.html", "/team.html", "/rules.html",
  "/console.html", "/integrate.html", "/data.html"];

test.describe("one origin", () => {
  test("the site and the API are served together", async ({ request }) => {
    expect((await request.get("/method.html")).status()).toBe(200);
    const health = await (await request.get("/v1/healthz")).json();
    expect(health.status).toBe("ok");
    const scored = await request.post("/v1/score", {
      data: { brief: "# Tool\nProblem: staff cannot update availability. Budget 30k. Ship by spring.", judge: "mock" },
    });
    expect(scored.status()).toBe(200);
    expect((await scored.json()).decision).toBeTruthy();
  });

  test("llms.txt is served, and points machines at the bar", async ({ request }) => {
    const r = await request.get("/llms.txt");
    expect(r.status()).toBe(200);
    const body = await r.text();
    expect(body).toContain("/v1/score");
    expect(body).toContain("Never invent or estimate a score");
  });

  test("the console can score against the same origin it is served from", async ({ page }) => {
    await page.goto("/console.html");
    await expect(page.locator("#input")).not.toBeEmpty();
    await page.locator("#run").click();
    // the mock judge answers instantly; a real number lands in the dial
    await expect(page.locator("#vscore")).not.toHaveText("—/100");
    await expect(page.locator("#gatestrip")).not.toBeEmpty();
  });
});

test.describe("chrome and navigation", () => {
  for (const path of PAGES) {
    test(`${path} carries the shared header and footer`, async ({ page }) => {
      await page.goto(path);
      await expect(page.locator(".wl-head")).toBeVisible();
      await expect(page.locator(".wl-foot")).toBeAttached();
      await expect(page.locator(".wl-cta-btn").last()).toHaveAttribute("href", /welance\.com\/directory/);
      await expect(page.locator(".wl-brandline")).toHaveAttribute("href", "./");
      // the project leads; welance is a small origin mark, not the headline
      await expect(page.locator(".wl-project")).toContainText("Perfect Brief");
    });
  }

  test("every internal link resolves", async ({ page, request }) => {
    const seen = new Set();
    for (const path of PAGES) {
      await page.goto(path);
      const hrefs = await page.locator("a[href$='.html'], a[href='./']").evaluateAll((as) =>
        as.map((a) => a.getAttribute("href")).filter((h) => !/^(https?:)?\/\//.test(h)));
      for (const h of hrefs) seen.add(h);
    }
    for (const href of seen) {
      const r = await request.get(href === "./" ? "/" : `/${href.replace(/^\.\//, "")}`);
      expect(r.status(), `${href} should resolve`).toBe(200);
    }
  });

  // The only hosts the public pages may touch: welance.com (the brand font),
  // Google Fonts (Noto fallbacks for CJK/Arabic in the console) and the Lottie
  // CDN on the landing ident. Anything else is a regression — a page that
  // phones home is a page a forker cannot trust.
  const ALLOWED_HOSTS = [
    "welance.com/fonts/",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "cdnjs.cloudflare.com/ajax/libs/lottie-web",
  ];

  test("no page reaches for an unexpected external host", async ({ page }) => {
    const external = [];
    page.on("request", (r) => {
      const u = new URL(r.url());
      if (!u.hostname.startsWith("127.0.0.1") && !u.hostname.startsWith("localhost")) external.push(u.href);
    });
    for (const path of PAGES) await page.goto(path);
    const unexpected = external.filter((u) => !ALLOWED_HOSTS.some((h) => u.includes(h)));
    expect(unexpected, `unexpected external requests: ${unexpected.join(", ")}`).toHaveLength(0);
  });
});

test.describe("eight languages, one choice", () => {
  test("the switcher offers all eight with flags", async ({ page }) => {
    await page.goto("/method.html");
    const options = page.locator("#langswitch option");
    await expect(options).toHaveCount(8);
    await expect(options.first()).toContainText("English");
  });

  test("choosing a language follows you across pages", async ({ page }) => {
    await page.goto("/method.html");
    await page.locator("#langswitch select").selectOption("it");
    await expect(page.locator("html")).toHaveAttribute("lang", "it");
    await page.goto("/team.html");
    await expect(page.locator("html")).toHaveAttribute("lang", "it");
    await expect(page.locator("[data-i18n='team.resh']")).toHaveText("Risultato");
  });

  test("Urdu and Arabic mirror the page", async ({ page }) => {
    for (const code of ["ur", "ar"]) {
      await page.goto(`/method.html?lang=${code}`);
      await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    }
    await page.goto("/method.html?lang=vi");
    await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  });

  test("English is restored exactly — the markup is the content of record", async ({ page }) => {
    await page.goto("/method.html?lang=en");
    const before = await page.locator("[data-i18n='method.eb1']").textContent();
    await page.locator("#langswitch select").selectOption("de");
    await page.locator("#langswitch select").selectOption("en");
    await expect(page.locator("[data-i18n='method.eb1']")).toHaveText(before);
  });

  test("unreviewed languages are labelled draft, English never is", async ({ page }) => {
    await page.goto("/method.html");
    const en = await page.locator("#langswitch option").first().textContent();
    expect(en).not.toContain("draft");
    const it = await page.locator("#langswitch option[value=it]").textContent();
    expect(it).toContain("draft");
  });
});

test.describe("the method reads at a glance", () => {
  test("the map, the ledger and the loop are all drawn", async ({ page }, testInfo) => {
    await page.goto("/method.html");
    // the hero map is a wide-screen affordance: hidden under 700px on purpose
    const wide = (page.viewportSize()?.width ?? 0) >= 700;
    await expect(page.locator(".m-ident svg")).toBeVisible({ visible: wide });
    await expect(page.locator(".bloop svg")).toBeVisible();
    await expect(page.locator(".fxrow")).toHaveCount(8);
    await expect(page.locator("#fxHead")).toContainText("8");
  });

  test("a formula opens to its plain-language line and its source", async ({ page }) => {
    await page.goto("/method.html");
    const row = page.locator(".fxrow").nth(3); // the share
    await row.locator("summary").click();
    await expect(row.locator(".fxbody")).toBeVisible();
    await expect(row.locator(".src")).toContainText("PERFECT-PRICE.md");
  });

  test("the fine print starts closed and opens on demand", async ({ page }) => {
    await page.goto("/");
    const fp = page.locator("details.fineprint").first();
    await expect(fp).not.toHaveAttribute("open", "");
    await fp.locator("summary").click();
    await expect(fp).toHaveAttribute("open", "");
  });

  /* The house style, enforced. welance.com's rhythm is: a short claim carries
     the section, ONE paragraph supports it, depth lives in the fine print.
     Prolixity is a UX bug — this test is how it stays fixed. */
  test("no paragraph on the surface runs longer than the style allows", async ({ page }) => {
    await page.goto("/method.html");
    const long = await page.evaluate(() => {
      const out = [];
      document.querySelectorAll(".wrap p, .wrap .door p, .wrap .step p").forEach((el) => {
        if (el.closest("details.fineprint")) return;       // depth is allowed to be long
        if (el.classList.contains("claim")) return;        // claims are short by construction
        const t = (el.textContent || "").trim();
        if (t.length > 360) out.push(t.slice(0, 60) + "… (" + t.length + ")");
      });
      return out;
    });
    expect(long, `too long on the surface: ${long.join(" | ")}`).toHaveLength(0);
  });

  test("brand bands break the page without breaking the layout", async ({ page }) => {
    for (const path of ["/method.html", "/"]) {
      await page.goto(path);
      await expect(page.locator(".band").first()).toBeVisible();
      // the band paints past the container; it must never widen the document
      const { scroll, client } = await page.evaluate(() => ({
        scroll: document.documentElement.scrollWidth,
        client: document.documentElement.clientWidth,
      }));
      expect(scroll, `${path} gained a horizontal scrollbar`).toBeLessThanOrEqual(client);
    }
  });

  test("the API example offers three languages, highlighted and copyable", async ({ page, context }) => {
    await page.goto("/");
    const blocks = page.locator(".code");
    await expect(blocks).toHaveCount(2);

    // highlighting is applied at runtime — the markup stays plain text
    await expect(blocks.first().locator(".u")).toContainText("briefs.welance.com");
    await expect(blocks.nth(1).locator(".k").first()).toContainText("score");
    await expect(blocks.nth(1).locator(".n").first()).toContainText("92.0");

    // the tabs switch the request language
    await expect(page.locator('pre[data-tab="curl"]')).toBeVisible();
    await page.locator('.code-tabs button[data-tab="py"]').click();
    await expect(page.locator('pre[data-tab="py"]')).toBeVisible();
    await expect(page.locator('pre[data-tab="curl"]')).toBeHidden();

    // copy yields clean code, not markup
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await blocks.first().locator(".code-copy").click();
    await expect(blocks.first().locator(".code-copy")).toHaveClass(/done/);
    const copied = await page.evaluate(() => navigator.clipboard.readText());
    expect(copied).toContain("import httpx");
    expect(copied).not.toContain("<span");
  });

  test("light and dark, remembered across pages, no flash", async ({ page }) => {
    await page.goto("/method.html");
    const theme = () => page.evaluate(() => document.documentElement.getAttribute("data-theme"));
    // the inline script decides before paint: the attribute is there immediately
    expect(await theme()).toMatch(/light|dark/);
    const before = await theme();
    await page.locator(".wl-theme").click();
    expect(await theme()).not.toBe(before);
    const chosen = await theme();
    await page.goto("/price.html");
    expect(await theme(), "the choice follows you").toBe(chosen);
  });

  test("the footer names its two columns and always shows docs and source", async ({ page }) => {
    await page.goto("/");
    const cols = page.locator(".wl-foot-links");
    await expect(cols).toHaveCount(2);
    await expect(page.locator('.wl-foot-links a[href="/docs"]')).toBeVisible();
    const gh = page.locator('.wl-foot-links a[href*="github.com"]');
    await expect(gh).toBeVisible();
    await expect(gh.locator("svg.wl-gh")).toBeVisible();
  });

  test("every section leads with a short claim", async ({ page }) => {
    await page.goto("/method.html");
    const claims = await page.locator(".claim").allTextContents();
    expect(claims.length).toBeGreaterThanOrEqual(4);
    for (const c of claims) expect(c.length, `claim too long: ${c}`).toBeLessThan(70);
  });

  test("the score × gate quadrant is on the rules page", async ({ page }) => {
    await page.goto("/rules.html");
    await expect(page.locator(".quad svg")).toBeVisible();
    await expect(page.locator(".quad")).toContainText("92/100");
  });
});
