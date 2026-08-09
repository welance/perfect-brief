/* The console must not offer a button that cannot do anything.
 *
 * The mock judge re-scores on every keystroke, so a "Score brief" button in
 * mock is a no-op: clicking it recomputes an identical verdict and nothing
 * visibly happens, which reads as broken. Mock therefore states what is
 * happening and offers the one judge that does need asking; live keeps the
 * button, because there the click is the thing that spends time and money.
 */
import { test, expect } from "@playwright/test";

test.describe("the score button is honest about what it does", () => {
  test("mock says it scores as you type instead of offering a dead button", async ({ page }) => {
    await page.goto("/console.html");
    await expect(page.locator("#run")).toBeHidden();
    await expect(page.locator("#scored")).toBeVisible();
    await expect(page.locator("#scored")).toContainText("scored as you type");
    await expect(page.locator("#livecta")).toBeVisible();
  });

  test("the score really does follow the typing, with no click at all", async ({ page }) => {
    await page.goto("/console.html");
    const readScore = async () =>
      (await page.locator("#vscore").innerText()).trim();
    const before = await readScore();
    await page.locator("#input").click();
    await page.keyboard.type(" Accessibility: WCAG 2.2 AA is expected.", { delay: 5 });
    await expect
      .poll(readScore, { message: "the mock judge should re-score while typing" })
      .not.toBe(before);
  });

  test("the publish CTA follows the gate, not the score", async ({ page }) => {
    await page.goto("/console.html");
    const cta = page.locator("#pubcta");

    await page.locator('[data-p="strong"]').click();
    await expect(cta).not.toHaveClass(/off/);
    await expect(cta).toHaveAttribute("href", /welance\.com\/en\/directory\/brief\/focus/);

    // the whole point of the gate: a high score that still may not publish
    await page.locator('[data-p="blocked"]').click();
    await expect(cta).toHaveClass(/off/);
    await expect(cta).not.toHaveAttribute("href", /./);
    await expect(page.locator("#vmeta")).not.toBeEmpty(); // and it says which rule
  });

  test("the CTA keeps the reader's language on the way to the Directory", async ({ page }) => {
    await page.goto("/console.html?lang=it");
    await page.locator('[data-p="strong"]').click();
    await expect(page.locator("#pubcta")).toHaveAttribute("href", /welance\.com\/it\//);
    await expect(page.locator("#pubcta")).toContainText("gratis");
  });

  test("the invitation switches to the live judge, where the button returns", async ({ page }) => {
    await page.goto("/console.html");
    await page.locator("#livecta").click();
    await expect(page.locator("#run")).toBeVisible();
    await expect(page.locator("#scored")).toBeHidden();
    await expect(page.locator("#livecta")).toBeHidden();
    await expect(page.locator("#modebtn")).toHaveClass(/live/);
  });
});
