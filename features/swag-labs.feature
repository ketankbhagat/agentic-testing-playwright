@browser
Feature: Swag Labs Purchase Flow - Functional UI Coverage
  As a Swag Labs customer
  I want to log in, add products to my cart, and complete checkout
  So that I can successfully purchase items end-to-end

  Background:
    Given I am on the Swag Labs login page

  Scenario: Successful login with standard_user lands on inventory page
    When I log in with username "standard_user" and password "secret_sauce"
    Then I should be redirected to "/inventory.html"
    And the inventory page should display the list of products

  Scenario: Locked out user is rejected with an error message
    When I log in with username "locked_out_user" and password "secret_sauce"
    Then I should remain on the login page
    And I should see the error message "Epic sadface: Sorry, this user has been locked out."

  Scenario: Adding Sauce Labs Backpack to cart updates the cart badge
    Given I am logged in as "standard_user" with password "secret_sauce"
    And I am on the inventory page
    When I add "Sauce Labs Backpack" to the cart
    Then the cart badge should display "1"

  Scenario: Complete purchase flow from login to order confirmation
    Given I am logged in as "standard_user" with password "secret_sauce"
    And I am on the inventory page
    When I add "Sauce Labs Backpack" to the cart
    And I navigate to the cart page
    Then the cart should contain "Sauce Labs Backpack"
    When I proceed to checkout
    And I fill in the checkout information with first name "John", last name "Doe", and zip code "12345"
    And I continue to the checkout overview
    Then the item total should be "$29.99"
    And the tax should be "$2.40"
    And the total should be "$32.39"
    When I finish the checkout
    Then I should be on the "/checkout-complete.html" page
    And I should see the message "Thank you for your order!"

@api
Feature: Swag Labs Purchase Flow - Session Enforcement Coverage
  As the Swag Labs system
  I want to enforce authentication on protected pages
  So that unauthenticated users cannot access restricted flows

  Scenario: Accessing inventory page without a login session is blocked
    Given I do not have an authenticated session
    When I send a direct GET request to "/inventory.html"
    Then the response should not return the inventory page content
    And I should be redirected to the login page or receive an access-denied response