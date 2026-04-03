# Route-Based CI Assignment System - Implementation Complete

## What Was Implemented

### 1. Database Schema Update
- Added `assigned_route` TEXT field to `users` table in `schema.sql`
- Created migration script `migrate_add_route.py` to update existing databases

### 2. Route Configuration
- Created `static/route_mapping.js` with 5 predefined routes:
  - Route 1: Bayawan → Kalumboyan → Border
  - Route 2: Bayawan → Candumao → Basay → Border
  - Route 3: Bayawan → Sipalay
  - Route 4: Bayawan → Santa Catalina
  - Route 5: Bayawan City Center

### 3. CI Staff Signup with Route Selection
- Updated `templates/signup.html`:
  - Added route dropdown (shows only for CI staff role)
  - Required field for CI staff
  - 5 route options to choose from
- Updated `app.py` signup route:
  - Validates route selection for CI staff
  - Saves assigned_route to database

### 4. Admin Route Management
- Updated `templates/manage_users.html`:
  - Shows assigned route for each CI staff in both pending and active tables
  - Added "Assign Route" button for CI staff without routes
  - Added "Edit" button to change existing routes
  - Modal dialog for route assignment
- Added `/update_ci_route` endpoint in `app.py`:
  - Allows admin to assign/change routes
  - Sends notification to CI staff when route is updated

### 5. Route-Based Application Assignment
- Updated `app.py` submit_application route:
  - Parses applicant's address (member_address field)
  - Matches address keywords to route definitions
  - Finds CI staff assigned to matching route
  - Assigns application to that CI staff
  - Falls back to workload-based assignment if no route match

### 6. CI Dashboard Route Display
- Updated `templates/ci_dashboard.html`:
  - Shows assigned route at top of dashboard
  - Alert message if no route assigned
  - Displays route name in user-friendly format

### 7. User Class Update
- Updated `User` class in `app.py`:
  - Added `assigned_route` parameter
  - Updated `load_user` function to load assigned_route

### 8. Area Field Auto-Fill
- Updated `templates/ci_application.html`:
  - Area field now auto-fills from `application.member_address`
  - Read-only field (no manual typing needed)

## How It Works

### For New CI Staff:
1. Register at `/signup`
2. Select "CI Staff" role
3. Route dropdown appears
4. Select assigned route (required)
5. Submit registration
6. Wait for admin approval

### For Existing CI Staff:
1. Admin goes to `/manage_users`
2. Finds CI staff in Active Users table
3. Clicks "Assign" or "Edit" button next to route column
4. Selects route from dropdown
5. Saves - CI staff gets notification

### For Loan Applications:
1. Loan staff submits application with member address
2. System reads address (e.g., "Kalumboyan, Bayawan City")
3. System matches "Kalumboyan" to Route 1
4. System finds CI staff assigned to Route 1
5. Application auto-assigned to that CI staff
6. If no match, falls back to lowest workload CI staff

### Route Matching Logic:
- Address is converted to lowercase
- System checks each route's keyword list
- First matching keyword determines the route
- Example: "Kalumboyan" → Route 1, "Basay" → Route 2, "Sipalay" → Route 3

## Migration Steps for Existing Database

1. **Backup your database first!**
   ```bash
   cp app.db app.db.backup
   ```

2. **Run migration script:**
   ```bash
   python migrate_add_route.py
   ```

3. **Assign routes to existing CI staff:**
   - Login as admin
   - Go to Manage Users
   - Click "Assign" button for each CI staff
   - Select their route

4. **Test the system:**
   - Submit a test application with address "Kalumboyan, Bayawan"
   - Verify it assigns to CI staff with Route 1

## Route Definitions

### Route 1: Bayawan → Kalumboyan → Border
Keywords: kalumboyan, kalamtukan, malabugas, bugay, nangka

### Route 2: Bayawan → Candumao → Basay → Border
Keywords: basay, actin, bal-os, bongalonan, cabalayongan, maglinao, nagbo-alao, olandao

### Route 3: Bayawan → Sipalay
Keywords: sipalay, cabadiangan, camindangan, canturay, cartagena, mambaroto, maricalum

### Route 4: Bayawan → Santa Catalina
Keywords: santa catalina, alangilan, amio, buenavista, caigangan, cawitan, manalongon, milagrosa, obat, talalak

### Route 5: Bayawan City Center
Keywords: ali-is, banaybanay, banga, boyco, cansumalig, dawis, manduao, mandu-ao, maninihon, minaba, narra, pagatban, poblacion, san isidro, san jose, san miguel, san roque, suba, tabuan, tayawan, tinago, ubos, villareal, villasol

## Benefits

1. **Fuel Efficiency**: CI staff travel one route, interview all applicants along the way
2. **No Backtracking**: Linear travel from start to end of route
3. **Predictable Workload**: Each CI knows their coverage area
4. **Automatic Assignment**: System handles routing logic
5. **Fallback Support**: Still works if no route matches (uses workload-based)

## Files Modified

- `schema.sql` - Added assigned_route column
- `app.py` - Updated signup, manage_users, submit_application, User class, load_user
- `templates/signup.html` - Added route selection dropdown
- `templates/manage_users.html` - Added route display and edit functionality
- `templates/ci_dashboard.html` - Added route display banner
- `templates/ci_application.html` - Auto-fill area field

## Files Created

- `static/route_mapping.js` - Route configuration and matching logic
- `migrate_add_route.py` - Database migration script
- `ROUTE_ASSIGNMENT_IMPLEMENTATION.md` - This documentation
