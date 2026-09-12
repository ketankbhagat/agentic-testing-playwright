# Swag Labs Data Model (Client-Side)

Note: SauceDemo is a static React app — no real backend database. All state is
managed in JavaScript/browser memory. This schema represents the logical data model.

## users (hardcoded)
- username: string (standard_user, locked_out_user, problem_user, performance_glitch_user)
- password: string (all use secret_sauce)
- status: active | locked

## products (static, 6 items)
- id: integer (0-5)
- name: string
- description: string
- price: decimal
- image_url: string

## cart (session state)
- items: array of product IDs
- persists in session only, no cookies or localStorage used for cart

## checkout
- firstName: string (required)
- lastName: string (required)
- postalCode: string (required)
- Validation: client-side only
