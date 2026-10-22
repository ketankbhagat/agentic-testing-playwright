import { test, expect } from '@playwright/test';

test.describe('Swag Labs — Purchase Flow', () => {

  test('1 — valid login redirects to inventory', async ({ page }) => {
    await page.goto('/');
    await page.locator('#user-name').fill('standard_user');
    await page.locator('#password').fill('secret_sauce');
    await page.locator('#login-button').click();

    await expect(page).toHaveURL(/.*inventory.html/);
    await expect(page.locator('[data-test="title"]')).toHaveText('Products');
  });

  test('2 — locked user sees error message', async ({ page }) => {
    await page.goto('/');
    await page.locator('#user-name').fill('locked_out_user');
    await page.locator('#password').fill('secret_sauce');
    await page.locator('#login-button').click();

    await expect(page).toHaveURL('https://www.saucedemo.com/');
    await expect(page.locator('[data-test="error"]')).toContainText('Epic sadface: Sorry, this user has been locked out.');
  });

  test('3 — add Backpack to cart shows badge', async ({ page }) => {
    await page.goto('/');
    await page.locator('#user-name').fill('standard_user');
    await page.locator('#password').fill('secret_sauce');
    await page.locator('#login-button').click();
    await expect(page).toHaveURL(/.*inventory.html/);

    await page.locator('[data-test="add-to-cart-sauce-labs-backpack"]').click();

    await expect(page.locator('.shopping_cart_badge')).toHaveText('1');
  });

  test('4 — complete purchase end to end', async ({ page }) => {
    await page.goto('/');
    await page.locator('#user-name').fill('standard_user');
    await page.locator('#password').fill('secret_sauce');
    await page.locator('#login-button').click();
    await expect(page).toHaveURL(/.*inventory.html/);

    await page.locator('[data-test="add-to-cart-sauce-labs-backpack"]').click();
    await expect(page.locator('.shopping_cart_badge')).toHaveText('1');

    await page.locator('.shopping_cart_link').click();
    await expect(page).toHaveURL(/.*cart.html/);
    await expect(page.locator('[data-test="inventory-item-name"]')).toHaveText('Sauce Labs Backpack');
    await expect(page.locator('[data-test="inventory-item-price"]')).toHaveText('$29.99');

    await page.locator('[data-test="checkout"]').click();
    await expect(page).toHaveURL(/.*checkout-step-one.html/);

    await page.locator('[data-test="firstName"]').fill('John');
    await page.locator('[data-test="lastName"]').fill('Doe');
    await page.locator('[data-test="postalCode"]').fill('12345');
    await page.locator('[data-test="continue"]').click();

    await expect(page).toHaveURL(/.*checkout-step-two.html/);
    await expect(page.locator('[data-test="subtotal-label"]')).toHaveText('Item total: $29.99');
    await expect(page.locator('[data-test="tax-label"]')).toHaveText('Tax: $2.40');
    await expect(page.locator('[data-test="total-label"]')).toHaveText('Total: $32.39');

    await page.locator('[data-test="finish"]').click();

    await expect(page).toHaveURL(/.*checkout-complete.html/);
    await expect(page.locator('.complete-header')).toHaveText('Thank you for your order!');

    await page.locator('[data-test="back-to-products"]').click();

    await expect(page).toHaveURL(/.*inventory.html/);
    await expect(page.locator('.shopping_cart_badge')).toHaveCount(0);
  });

  test('5 — inventory page requires authentication', async ({ page }) => {
    await page.goto('/inventory.html');

    await expect(page).toHaveURL('https://www.saucedemo.com/');
    await expect(page.locator('[data-test="error"]')).toBeVisible();
    await expect(page.locator('[data-test="error"]')).toContainText("Epic sadface: You can only access '/inventory.html' when you are logged in.");
  });

});