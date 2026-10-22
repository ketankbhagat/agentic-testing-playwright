@purchase_flow
Feature: Swag Labs end-to-end purchase flow
  As a customer of Swag Labs
  I want to log in, add products to my cart, and complete checkout
  So that I can successfully purchase items online

  Background:
    Given I am on the Swag Labs login page

  @browser @login @smoke
  Scenario: Successful login with standard_user lands on inventory page
    When I log in with username "standard_user" and password "secret_sauce"
    Then I should be redirected to "/inventory.html"
    And I should see the products inventory page

  @browser @login @negative
  Scenario: Locked out user receives rejection error message
    When I log in with username "locked_out_user" and password "secret_sauce"
    Then I should remain on the login page
    And I should see an error message "Epic sadface: Sorry, this user has been locked out."

  @browser @cart
  Scenario: Add Sauce Labs Backpack to cart updates cart badge
    Given I log in with username "standard_user" and password "secret_sauce"
    And I am on the inventory page
    When I add "Sauce Labs Backpack" to the cart
    Then the cart badge should display "1"

  @browser @e2e @smoke
  Scenario: Complete purchase flow from login to order confirmation
    Given I log in with username "standard_user" and password "secret_sauce"
    And I am on the inventory page
    When I add "Sauce Labs Backpack" to the cart
    Then the cart badge should display "1"
    When I go to the cart page
    Then I should see "Sauce Labs Backpack" in the cart with price "$29.99"
    When I click the checkout button
    And I fill in the checkout information with first name "John", last name "Doe", and postal code "12345"
    And I click continue
    Then I should see the item total as "$29.99"
    And I should see the tax as "$2.40"
    And I should see the total as "$32.39"
    When I click finish
    Then I should be redirected to "/checkout-complete.html"
    And I should see the message "Thank you for your order!"
    When I click back home
    Then I should be redirected to "/inventory.html"
    And the cart badge should not be displayed

  @api @security @negative
  Scenario: Accessing inventory page without an authenticated session is rejected
    Given I do not have an active login session
    When I send a request to access "/inventory.html" directly
    Then the response should not return the inventory page content
    And I should be redirected to the login page or receive an access denied error