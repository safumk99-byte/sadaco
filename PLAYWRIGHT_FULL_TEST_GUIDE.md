# SADACO Full Playwright Test Suite

This project includes an end-to-end smoke/regression suite for the React + Vite frontend.

## 1. Start Django

From the project root:

```bash
python manage.py runserver
```

## 2. Start React

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

## 3. Install Playwright

From the project root:

```bash
npm install
npx playwright install chromium
```

## 4. Set test credentials

Do not put the password in source code.

CMD:

```cmd
set SADACO_TEST_USERNAME=safumk
set SADACO_TEST_PASSWORD=YOUR_PASSWORD
```

PowerShell:

```powershell
$env:SADACO_TEST_USERNAME="safumk"
$env:SADACO_TEST_PASSWORD="YOUR_PASSWORD"
```

## 5. Run the complete suite

```bash
npm run test:e2e:full
```

or:

```bash
npx playwright test tests/sadaco.full.spec.js
```

## What the full suite checks

- Login page
- Customer registration page
- Authentication
- Dashboard
- Management navigation
- Staff
- Tasks
- Attendance
- Performance
- Products
- Stock
- Sales
- Customer Requests
- Enquiries
- Production
- Quality
- Purchase
- Finance
- Delivery
- Marketing
- Reports
- Users & Roles
- Approval Center
- Audit Trail
- My Profile
- Customer Portal route
- Mobile navigation
- Logout
- Browser console errors
- Uncaught page errors
- API 5xx responses
- Failed API/source requests

## Reports

After a run:

```bash
npx playwright show-report
```

Screenshots, video, and traces are retained for failed tests according to `playwright.config.js`.
