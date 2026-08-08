/* The public surface: one origin, nine languages, no dead ends.
 *
 * These are the promises a visitor and a forker both rely on — the pages and
 * the API live together, every page carries the same chrome, the language
 * follows you, and nothing on the site reaches for an external host.
 */
import { test, expect } from "@playwright/test";

const PAGES = ["/", "/method.html", "/price.html", "/team.html", "/rules.html",
  "/console.html", "/integrate.html", "/data.html"];


// On a phone the language switch lives inside the menu panel, so it has to be
// opened first — the same two taps a visitor makes.
async function chooseLanguage(page, code) {
  const burger = page.locator(".wl-burger");
  if (await burger.isVisible()) {
    const panel = page.locator(".wl-menu");
    if (!(await panel.isVisible())) await burger.click();
  }
  await page.locator("#langswitch select").selectOption(code);
}

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

test.describe("nine languages, one choice", () => {
  test("the switcher offers every language with a flag", async ({ page }) => {
    await page.goto("/method.html");
    const options = page.locator("#langswitch option");
    const { LANGS } = await page.evaluate(() => ({ LANGS: WelanceI18n.LANGS.map((l) => l.code) }));
    await expect(options).toHaveCount(LANGS.length);
    // on a phone the chosen language shortens to "🇬🇧 EN" so the header still
    // fits; the list keeps naming every language, and so does the a11y name
    await expect(options.first()).toHaveAttribute("aria-label", "English");
  });

  test("every declared language actually has a dictionary", async ({ page }) => {
    // a flag in the switcher with no strings behind it is worse than no flag
    await page.goto("/method.html");
    const thin = await page.evaluate(async () => {
      const out = [];
      for (const l of WelanceI18n.LANGS) {
        if (l.code === "en") continue;
        WelanceI18n.set(l.code);
        const untranslated = [...document.querySelectorAll("[data-i18n], [data-i18n-html]")]
          .filter((el) => !el.textContent.trim()).length;
        if (untranslated) out.push(`${l.code}: ${untranslated} empty`);
      }
      return out;
    });
    expect(thin, thin.join(" | ")).toHaveLength(0);
  });

  test("choosing a language follows you across pages", async ({ page }) => {
    await page.goto("/method.html");
    await chooseLanguage(page, "it");
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
    await chooseLanguage(page, "de");
    await chooseLanguage(page, "en");
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

test.describe("the ways in", () => {
  test("every route on the integrate page leads somewhere real", async ({ page, request }) => {
    await page.goto("/integrate.html");
    await expect(page.locator(".route")).toHaveCount(4);
    for (const href of await page.locator(".route .go").evaluateAll((as) => as.map((a) => a.getAttribute("href")))) {
      if (href.startsWith("#")) {
        await expect(page.locator(href)).toBeAttached();
      } else {
        expect((await request.get(href)).status(), `${href} should resolve`).toBeLessThan(400);
      }
    }
  });

  test("the works-with matrix is honest about MCP, prompt and API", async ({ page }) => {
    await page.goto("/integrate.html");
    const rows = page.locator(".works tbody tr");
    await expect(rows).toHaveCount(5);
    // Claude and ChatGPT both do all three — the earlier badges implied otherwise
    const claude = rows.filter({ hasText: "Claude" });
    await expect(claude.locator("td.y")).toHaveCount(3);
    const gpt = rows.filter({ hasText: "ChatGPT" });
    await expect(gpt.locator("td.y")).toHaveCount(3);
    // code and CI can only call the API, and the table says so
    await expect(rows.last().locator("td.n")).toHaveCount(2);
  });

  test("the MCP snippet is the command we actually publish", async ({ page }) => {
    await page.goto("/integrate.html");
    const cfg = page.locator('pre[data-lang="json"]');
    await expect(cfg).toContainText("uvx");
    await expect(cfg).toContainText("subdirectory=mcp-server");
    await expect(cfg).toContainText("perfect-brief-mcp");
  });

  test("the console offers a calmer place to write", async ({ page }) => {
    await page.goto("/console.html");
    const cta = page.locator(".focus-cta");
    await expect(cta).toBeVisible();
    await expect(cta).toHaveAttribute("href", /welance\.com\/directory\/brief\/focus/);
  });
});

test.describe("the language a visitor expects", () => {
  test("a German browser gets German without a redirect", async ({ browser }) => {
    const ctx = await browser.newContext({ locale: "de-DE" });
    const page = await ctx.newPage();
    const responses = [];
    page.on("response", (r) => responses.push(r.status()));
    await page.goto("/method.html");
    await expect(page.locator("html")).toHaveAttribute("lang", "de");
    expect(responses.filter((s) => s >= 300 && s < 400), "no redirects").toHaveLength(0);
    await ctx.close();
  });

  test("a regional variant falls back to the closest we have", async ({ browser }) => {
    const ctx = await browser.newContext({ locale: "pt-PT" });
    const page = await ctx.newPage();
    await page.goto("/method.html");
    await expect(page.locator("html")).toHaveAttribute("lang", "pt-BR");
    await ctx.close();
  });

  test("an explicit choice always beats the browser, and is remembered", async ({ browser }) => {
    const ctx = await browser.newContext({ locale: "de-DE" });
    const page = await ctx.newPage();
    await page.goto("/method.html?lang=it");
    await expect(page.locator("html")).toHaveAttribute("lang", "it");
    await page.goto("/team.html");
    await expect(page.locator("html"), "the choice sticks").toHaveAttribute("lang", "it");
    await ctx.close();
  });

  test("an unknown language lands on English, not on nothing", async ({ browser }) => {
    const ctx = await browser.newContext({ locale: "ja-JP" });
    const page = await ctx.newPage();
    await page.goto("/method.html");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await ctx.close();
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

  test("every formula opens to its plain line and links to where it is defined", async ({ page }) => {
    await page.goto("/method.html");
    const rows = page.locator(".fxrow");
    await expect(rows).toHaveCount(8);
    for (let i = 0; i < 8; i++) {
      const row = rows.nth(i);
      await row.locator("summary").click();
      await expect(row.locator(".fxbody")).toBeVisible();
      const link = row.locator(".src a");
      await expect(link, "a formula must say where it is defined").toHaveAttribute(
        "href", /github\.com\/welance\/perfect-brief\/blob\/main\//);
    }
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

  test("the header holds at every width, not only the two we test on", async ({ page }) => {
    // it has broken three times now, always between the phone and the laptop:
    // five nav names, a language select and the pill competing for one line
    const broken = [];
    for (const width of [412, 560, 640, 768, 900, 960, 1024, 1100, 1180, 1280, 1440, 1600]) {
      await page.setViewportSize({ width, height: 800 });
      await page.goto("/method.html");
      const over = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      if (over > 0) broken.push(`${width}px overflows by ${over}px`);
    }
    expect(broken, broken.join(" | ")).toHaveLength(0);
  });

  test("the way out of the page survives a phone, in every language", async ({ page }) => {
    // the pill is the one link that leads somewhere else — it does not get
    // dropped for being inconvenient at 320px
    const broken = [];
    for (const lang of ["en", "es", "pt-BR", "ar", "vi"]) {
      for (const width of [320, 390, 412, 560]) {
        await page.setViewportSize({ width, height: 800 });
        await page.goto(`/method.html?lang=${lang}`);
        const pill = page.locator(".wl-pill");
        await expect(pill).toBeVisible();
        const fits = await page.evaluate(() => {
          const b = document.querySelector(".wl-pill").getBoundingClientRect();
          const vw = document.documentElement.clientWidth;
          return { inside: b.left >= -0.5 && b.right <= vw + 0.5,
                   over: document.documentElement.scrollWidth - vw };
        });
        if (!fits.inside || fits.over > 0) broken.push(`${lang}@${width}px`);
      }
    }
    expect(broken, broken.join(" ")).toHaveLength(0);
  });

  test("the header carries three ways in, and the rest lives in the footer", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator(".wl-nav .wl-nav-item")).toHaveCount(3);
    await expect(page.locator(".wl-nav")).toContainText("The calculators");
    // the calculators page is the index the menu no longer has to be
    await page.goto("/calculators.html");
    for (const href of ["index.html", "price.html", "team.html"]) {
      await expect(page.locator(`.tool a[href="${href}"]`)).toBeVisible();
    }
  });

  test("choosing a language writes it into the address", async ({ page }) => {
    await page.goto("/method.html");
    await chooseLanguage(page, "it");
    await expect(page).toHaveURL(/\/it\/method\.html$/);
    // and following any relative link keeps you in that language — the footer
    // one, because the header nav is not on a phone
    await page.locator('.wl-foot-links a[href="calculators.html"]').click();
    await expect(page).toHaveURL(/\/it\/calculators\.html$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "it");
  });

  test("the invitation to change the rules is visible in every language", async ({ page }) => {
    // an open ruleset is only open if changing it is something a reader can
    // picture themselves doing — so the clause is marked, and it is a link
    for (const lang of ["en", "it", "de", "ar"]) {
      await page.goto(`/?lang=${lang}`);
      const hl = page.locator("p .hl");
      await expect(hl).toBeVisible();
      await expect(hl).toHaveAttribute("href", /GOVERNANCE\.md$/);
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

  test("the source is one click from every page, the theme lives in the footer", async ({ page }) => {
    await page.goto("/");
    const src = page.locator('.wl-head .wl-src[href*="github.com"]');
    await expect(src).toBeVisible();
    await expect(src.locator("svg")).toBeVisible();
    await expect(page.locator(".wl-head .wl-theme")).toHaveCount(0);
    await expect(page.locator(".wl-foot-bottom .wl-theme")).toBeVisible();
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
