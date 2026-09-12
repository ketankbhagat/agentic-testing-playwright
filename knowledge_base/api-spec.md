# API / Route Specification

Note: SauceDemo is a React SPA. No REST API — all routes are client-side.
However, direct URL access behavior is testable:

## GET / (login page)
- Always accessible
- If already logged in, stays on login page (no auto-redirect to inventory)

## GET /inventory.html
- Requires valid login session
- Without login: shows error "Epic sadface: You can only access '/inventory.html' when you are logged in."
- With login: displays 6 products

## GET /cart.html
- Requires login session
- Shows current cart contents

## GET /checkout-step-one.html
- Requires login session
- Checkout form

## GET /checkout-step-two.html
- Requires login session + checkout step one completed
- Order summary

## GET /checkout-complete.html
- Requires login session + order placed
- Thank you confirmation

## MISSING:
- No documented behavior for deep-linking to checkout without items in cart
- No specification for concurrent session handling
- No rate limiting or brute force protection on login
