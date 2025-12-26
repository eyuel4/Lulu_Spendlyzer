# Plaid Integration - Quick Start Guide 🚀

## Prerequisites
- Plaid account with sandbox credentials
- Backend running on port 8000
- Frontend running on port 4200

## Step 1: Configure Plaid Credentials

Create or update your `.env` file in the project root:

```env
PLAID_CLIENT_ID=your_client_id_here
PLAID_SECRET=your_secret_here
PLAID_ENV=sandbox
PLAID_WEBHOOK_URL=http://localhost:8000/api/plaid/webhook
```

**Get Your Credentials:**
1. Sign up at https://dashboard.plaid.com/signup
2. Go to Team Settings → Keys
3. Copy your `client_id` and `secret` (sandbox)
4. Enable **Transactions** and **Auth** products

## Step 2: Install Dependencies

### Backend:
```bash
pip install -r requirements.txt
```

### Frontend:
```bash
cd spendlyzer-frontend
npm install
```

## Step 3: Update Database

```bash
python -m app.core.init_db
```

This adds the new Plaid fields to the Card table.

## Step 4: Start Services

### Terminal 1 - Backend:
```bash
python -m uvicorn app.main:app --reload --port 8000
```

You should see:
```
✅ Logging service initialized successfully
✅ Plaid sync scheduler initialized successfully (daily at 2 AM)
```

### Terminal 2 - Frontend:
```bash
cd spendlyzer-frontend
npm start
```

## Step 5: Test the Integration

### Connect a Bank Account:

1. **Open Dashboard**
   - Navigate to http://localhost:4200/dashboard
   - Login to your account

2. **Click "Connect Bank"**
   - In the Quick Actions section
   - Plaid Link will open

3. **Select Test Institution**
   - Choose "First Platypus Bank" or "Tartan Bank"
   - Username: `user_good`
   - Password: `pass_good`

4. **Complete Connection**
   - Select account(s)
   - Click Continue
   - Wait for initial sync

5. **Verify Success**
   - You should see a success message
   - Connected banks count will update
   - Transactions will appear in your dashboard

### View Connected Banks:

1. Click "Manage Banks" button (appears after connecting)
2. Or navigate to http://localhost:4200/connected-banks
3. You'll see:
   - All connected banks
   - Last sync date
   - Sync Now button
   - Disconnect option

### Manual Sync:

1. Go to Connected Banks page
2. Click "Sync Now" on any bank
3. Watch the sync status update
4. New transactions will be added

### Disconnect a Bank:

1. Go to Connected Banks page
2. Click "Disconnect" on any bank
3. Confirm in the modal
4. Bank will be removed (transactions remain)

## Troubleshooting

### "Plaid is not defined" Error
**Solution:** The Plaid script is already added to `index.html`. Clear browser cache and reload.

### "Failed to create link token"
**Solution:** 
- Check `.env` has correct credentials
- Restart backend after adding credentials
- Verify Plaid Dashboard shows active sandbox

### No Transactions After Sync
**Solution:**
- Check backend logs for errors
- Verify test institution has transactions
- Try "First Platypus Bank" with `user_good`/`pass_good`

### Scheduler Not Running
**Solution:**
- Check backend startup logs
- Look for "Plaid sync scheduler initialized"
- Verify `apscheduler` is installed

## Testing Different Scenarios

### Test Successful Connection:
- Institution: "First Platypus Bank"
- Username: `user_good`
- Password: `pass_good`
- Result: Should connect and sync transactions

### Test Error Handling:
- Institution: "First Platypus Bank"
- Username: `user_bad`
- Password: `pass_good`
- Result: Should show error message

### Test Duplicate Prevention:
1. Connect a bank
2. Sync manually
3. Sync again immediately
4. Result: No duplicate transactions

## API Endpoints

Test with curl or Postman:

```bash
# Get link token
curl -X POST http://localhost:8000/plaid/create-link-token \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"

# Get connected accounts
curl http://localhost:8000/plaid/accounts \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Manual sync
curl -X POST http://localhost:8000/plaid/sync-transactions/1 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Next Steps

### For Development:
- ✅ Integration is complete and working
- ✅ Test all features thoroughly
- ✅ Review logs for any errors

### For Production:
1. Apply for Plaid Production access
2. Update `PLAID_ENV=production` in `.env`
3. Deploy to server with HTTPS
4. Update `PLAID_WEBHOOK_URL` with public URL
5. Configure webhooks in Plaid Dashboard

## Features Available

✅ **Connect Banks** - Secure connection through Plaid  
✅ **Auto Sync** - Daily at 2 AM automatically  
✅ **Manual Sync** - On-demand sync button  
✅ **View Banks** - See all connected accounts  
✅ **Disconnect** - Remove banks anytime  
✅ **Deduplication** - No duplicate transactions  
✅ **Last 30 Days** - Syncs recent transactions  
✅ **Mobile Ready** - Responsive design  
✅ **Dark Mode** - Full dark mode support  

## Support

**Backend Logs:**
```bash
# Watch backend logs
python -m uvicorn app.main:app --reload --port 8000
```

**Frontend Console:**
- Open browser DevTools (F12)
- Check Console tab for errors
- Check Network tab for API calls

**Common Log Messages:**
- ✅ "Plaid sync scheduler initialized" - Scheduler working
- ✅ "Link token created for user X" - Token generation working
- ✅ "Token exchanged successfully" - Bank connected
- ✅ "Sync completed for card X" - Transactions synced

## Success Checklist

- [ ] Plaid credentials configured in `.env`
- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Can click "Connect Bank" button
- [ ] Plaid Link opens successfully
- [ ] Can connect test bank account
- [ ] Transactions sync after connection
- [ ] Can see connected banks
- [ ] Manual sync works
- [ ] Can disconnect banks
- [ ] No duplicate transactions
- [ ] Scheduler shows in startup logs

🎉 **You're all set! Happy testing!**

