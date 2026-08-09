/* Typing a rate must survive the keystroke.
 *
 * renderRows() clears #rows and rebuilds every row from scratch. Any input
 * inside it that calls render() on "input" destroys the node the user is
 * typing into, so focus is lost after one character and a 2-4 digit rate
 * becomes impossible to enter. Regression guard for that whole class.
 */
import { test, expect } from "@playwright/test";

test.describe("team.html rate fields keep focus", () => {
  test("a per-role rate accepts a multi-digit number in one go", async ({ page }) => {
    await page.goto("/team.html");
    const own = page.locator('#rows input[type="number"]').first();
    await own.click();
    await own.fill("");
    await page.keyboard.type("1250", { delay: 40 });

    // the field the user started in must still be the one receiving keystrokes
    await expect(own).toBeFocused();
    await expect(own).toHaveValue("1250");
  });

  // #floorc is a <select>, not a typed field — nothing to lose focus there.
  test("the client rate accepts a multi-digit number too", async ({ page }) => {
    await page.goto("/team.html");
    const field = page.locator("#rate");
    await field.click();
    await field.fill("");
    await page.keyboard.type("1450", { delay: 40 });
    await expect(field, "#rate lost focus while typing").toBeFocused();
    await expect(field).toHaveValue("1450");
  });
});
