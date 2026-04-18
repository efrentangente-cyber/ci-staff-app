# Quick Start Guide - Permissions System

## For Super Admin

### How to Manage Loan Officer Permissions

1. **Login as Super Admin**
   - Email: `superadmin@dccco.test`
   - Password: (your password)

2. **Navigate to Permissions**
   - Click "Manage Permissions" in the sidebar
   - Or go to: `/manage_permissions`

3. **View Loan Officers**
   - See list of all loan officers
   - Green badge = Permission granted
   - Gray badge = Permission denied

4. **Edit Permissions**
   - Click "Edit" button next to loan officer name
   - Check/uncheck permissions:
     - ☑ Manage Users - Can approve users, view all users
     - ☑ System Settings - Can configure system, manage loan types
   - Click "Update Permissions"

5. **Changes Take Effect**
   - Immediately for new logins
   - Existing sessions need logout/login

## For Loan Officers

### What Permissions Mean

#### Without Any Permissions:
- ✅ Can review applications
- ✅ Can view CI checklists
- ✅ Can approve/reject loans
- ✅ Can view reports
- ❌ Cannot manage users
- ❌ Cannot access system settings

#### With "Manage Users" Permission:
- ✅ All default access above
- ✅ Can approve/reject user registrations
- ✅ Can view all active users
- ✅ Can manage user roles
- ✅ See "Manage Users" in sidebar

#### With "System Settings" Permission:
- ✅ All default access above
- ✅ Can configure system settings
- ✅ Can manage loan types
- ✅ Can view system statistics
- ✅ See "System Settings" in sidebar

### How to Request Permissions

1. Contact super admin
2. Explain which permissions you need
3. Super admin will grant access
4. Logout and login again
5. New menu items will appear

## Testing the System

### Test as Super Admin:
```
1. Login as superadmin@dccco.test
2. Click "Manage Permissions"
3. Click "Edit" on loan officer
4. Uncheck "Manage Users"
5. Click "Update Permissions"
6. Logout
```

### Test as Loan Officer (Without Permission):
```
1. Login as admin@dccco.test
2. "Manage Users" should NOT be in sidebar
3. Try to access /manage_users directly
4. Should redirect with "Access Denied" message
5. Logout
```

### Test as Super Admin (Grant Permission):
```
1. Login as superadmin@dccco.test
2. Click "Manage Permissions"
3. Click "Edit" on loan officer
4. Check "Manage Users"
5. Click "Update Permissions"
6. Logout
```

### Test as Loan Officer (With Permission):
```
1. Login as admin@dccco.test
2. "Manage Users" should be in sidebar
3. Click "Manage Users"
4. Should work normally
5. Can approve/reject users
```

## Troubleshooting

### Problem: Loan officer can't see menu item
**Solution**: 
1. Super admin needs to grant permission
2. Loan officer needs to logout and login

### Problem: Changes not taking effect
**Solution**: 
1. Clear browser cache
2. Logout and login again
3. Check permissions in database

### Problem: Access denied error
**Solution**: 
1. This is normal if no permission
2. Contact super admin to request access
3. Super admin grants permission
4. Logout and login

### Problem: Super admin can't access manage permissions
**Solution**: 
1. Verify role is 'admin' in database
2. Check URL is correct: /manage_permissions
3. Clear browser cache

## Database Commands (For Developers)

### Check current permissions:
```bash
python check_permissions.py
```

### Manually grant all permissions:
```sql
UPDATE users 
SET permissions = 'manage_users,system_settings' 
WHERE email = 'admin@dccco.test';
```

### Manually revoke all permissions:
```sql
UPDATE users 
SET permissions = NULL 
WHERE email = 'admin@dccco.test';
```

### Check permissions in database:
```sql
SELECT name, email, role, permissions 
FROM users 
WHERE role IN ('admin', 'loan_officer');
```

## Security Notes

1. **Super admin always has full access** - Cannot be restricted
2. **Permissions are additive** - Grant only what's needed
3. **Changes are immediate** - But require re-login
4. **Menu items auto-hide** - No broken links
5. **Routes are protected** - Direct URL access blocked

## Default Permissions

When system is first deployed:
- Super Admin: No permissions needed (full access by role)
- Loan Officers: Both permissions granted by default
- You can revoke as needed

## Best Practices

1. **Principle of Least Privilege**
   - Only grant permissions that are needed
   - Review permissions regularly

2. **Regular Audits**
   - Check who has what permissions
   - Remove unnecessary access

3. **Clear Communication**
   - Inform users when permissions change
   - Explain what each permission allows

4. **Documentation**
   - Keep track of permission changes
   - Document why permissions were granted

## Quick Reference

| Permission | Allows Access To |
|-----------|------------------|
| `manage_users` | User management, approvals, role assignments |
| `system_settings` | System config, loan types, statistics |
| None | Application review, decisions, reports only |

---

**Need Help?** Contact system administrator or refer to PERMISSIONS_SYSTEM_COMPLETE.md for detailed documentation.
