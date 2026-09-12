# JIRA-201: Swag Labs Login

**Status:** Done
**Sprint:** Sprint 1
**Acceptance Criteria:**
- Login page renders at /
- standard_user can log in with password secret_sauce
- Successful login redirects to /inventory.html
- locked_out_user sees error "Epic sadface: Sorry, this user has been locked out."
- Empty username shows "Epic sadface: Username is required"
- Empty password shows "Epic sadface: Password is required"
- Error messages are dismissible via X button

**Selectors:**
- Username: #user-name
- Password: #password
- Login button: #login-button
- Error: [data-test="error"]

**Test Users:**
| Username | Password | Behavior |
|----------|----------|----------|
| standard_user | secret_sauce | Normal user |
| locked_out_user | secret_sauce | Blocked — error message |
| problem_user | secret_sauce | Buggy images and behavior |
| performance_glitch_user | secret_sauce | Slow responses |

**Notes:** React SPA. All routing is client-side. No server-rendered pages.
