# Video Script — Secure your Serverless API in AWS (Cognito + API Gateway)

---

## Introduction

[ Screen recording of the Notes Demo web app — logging in via Cognito Hosted UI, then creating and deleting notes ]

"In the last video we built a serverless CRUD API on AWS using Lambda, DynamoDB, and API Gateway. In this video we secure it with real user authentication using Amazon Cognito."

[ Architecture diagram — walk through it: browser, S3, Cognito, API Gateway, Lambda, DynamoDB ]

"We'll add a Cognito User Pool with a Hosted UI, a PKCE OAuth2 login flow, and a JWT authorizer on API Gateway — so every API call is verified before Lambda ever runs."

[ Terminal running apply.sh — Terraform output, ending with the website URL ]

"Follow along and in minutes you'll have a working authenticated API running in AWS."

---

## Architecture

[ Full diagram ]

"Let's walk through the architecture before we build."

[ Highlight browser and S3 bucket ]

"The user opens a static web app served from S3. Unlike the previous project, this app has two pages — index.html and callback.html."

[ Highlight Cognito ]

"When the user clicks Login, the browser redirects to the Cognito Hosted UI. The user signs in there — we never handle credentials ourselves."

[ Highlight callback.html ]

"After login, Cognito redirects back to callback.html with an authorization code. The page exchanges that code for tokens using the PKCE flow — and stores the access token in sessionStorage."

[ Highlight API Gateway → JWT authorizer ]

"Every API call from the frontend includes that access token as a Bearer header. API Gateway validates it against the Cognito JWKS endpoint before Lambda ever runs."

[ Highlight Lambda → DynamoDB ]

"Lambda extracts the Cognito sub claim from the verified JWT and uses it as the DynamoDB partition key. Each user's notes are completely isolated at the storage layer."

---

## Build the Code

[ Terminal — running ./apply.sh ]

"The whole deployment is one script — apply.sh. Two phases."

[ Terminal — Phase 1: Terraform apply in 01-lambdas ]

"Phase one: Terraform provisions the Cognito User Pool, Hosted UI domain, and app client — then the DynamoDB table, all five Lambda functions, and the API Gateway with its JWT authorizer."

[ Terminal — config.json being generated ]

"Between phases, the script reads the Cognito and API Gateway outputs from Terraform and writes config.json — the Cognito domain, client ID, redirect URI, and API base URL that the frontend needs at runtime."

[ Terminal — Phase 2: Terraform apply in 02-webapp ]

"Phase two: Terraform uploads index.html, callback.html, and config.json to S3. The site is live."

[ Terminal — deployment complete, URL printed ]

"Website URL. Done."

---

## Build Results

[ AWS Console — us-east-1 resources ]

"Let's look at what was deployed."

[ AWS Console — Cognito User Pool ]

"First — the Cognito User Pool. This is where user accounts live. Email-based sign-in, no custom code needed."

[ AWS Console — Cognito App Client ]

"The app client is configured for Authorization Code with PKCE — no client secret, safe for a browser SPA."

[ AWS Console — API Gateway, notes-api, Authorizers tab ]

"Next — the API Gateway. The JWT authorizer is attached here. It validates the issuer against the Cognito User Pool endpoint and the audience against the app client ID."

[ Show Routes ]

"The five routes are unchanged from the previous project — each one wired to its own Lambda."

[ AWS Console — Lambda functions list ]

"Five Lambda functions, one per operation, each with a least-privilege IAM role."

[ AWS Console — DynamoDB table, notes-cognito ]

"The DynamoDB table looks the same, but the partition key is now the Cognito sub claim — a unique, stable ID per user — instead of the hardcoded 'global' owner from before."

[ AWS Console — S3 bucket ]

"Finally, the S3 bucket hosts the three frontend files — index.html, callback.html, and the generated config.json."

[ Browser — Notes Demo login page ]

"Open the website URL to launch the app."

---

## Demo

[ Browser — Notes Demo, Login button visible ]

"The app loads. We're not logged in yet — the note list is empty and the controls are disabled."

[ Clicking Login — Cognito Hosted UI opens ]

"Click Login. The browser redirects to the Cognito Hosted UI."

[ Creating a new user account or signing in ]

"Sign in with an existing account — or create one here."

[ Cognito redirects back to callback.html ]

"Cognito redirects back to callback.html. The page exchanges the authorization code for tokens and stores the access token in sessionStorage."

[ Browser — Notes Demo, now logged in, DevTools → Network tab ]

"We're back in the app, now authenticated. Open DevTools so we can watch the API calls."

[ Refresh — GET /notes call visible with Authorization header ]

"The app calls the list endpoint — and you can see the Bearer token in the Authorization header."

[ Clicking New — modal opens, typing a title, clicking Create ]

"Create a new note."

[ Show network tab — POST with auth header ]

"A POST is made with the JWT. API Gateway validates it, Lambda extracts the sub, and the note is stored under this user's partition key."

[ Editing and clicking Save ]

"Update the note."

[ Show network tab ]

"A PUT call — same auth flow."

[ Clicking Delete ]

"Delete the note."

[ Browser — empty list ]

"In this demo we've exercised every API endpoint — all secured with Cognito JWT authentication."

---
