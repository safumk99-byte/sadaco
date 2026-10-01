# SADACO Playwright E2E Testing

This update adds a Playwright end-to-end test suite without adding `node_modules` or browser binaries to the ZIP.

## 1. Install Playwright

From the project root:

```bash
npm install
npx playwright install chromium
```

## 2. Start Django

In one terminal, from the project root:

```bash
venv\\Scripts\\activate
python manage.py runserver
```

## 3. Start React/Vite

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

## 4. Set the test password

Do not put the real password in source code.

PowerShell:

```powershell
$env:SADACO_TEST_PASSWORD="YOUR_PASSWORD"
```

CMD:

```cmd
set SADACO_TEST_PASSWORD=YOUR_PASSWORD
```

## 5. Run the test

From the project root:

```bash
npx playwright test
```

The current test validates:

- React login page loads
- `safumk` can authenticate
- Dashboard opens
- API 5xx responses are detected
- Browser console errors are detected

HTML report:

```bash
npx playwright show-report
```
