# Requirements Document

## Introduction

This document specifies requirements for implementing a geographic route-based CI (Credit Investigator) assignment system for the DCCCO loan management application. The system will replace the current workload-based assignment with a geographic route-based approach to minimize travel and fuel costs. Each CI staff member will be assigned one linear road route, and they will only receive applications from barangays along their assigned route.

## Glossary

- **CI_Staff**: Credit Investigator staff members who conduct field interviews with loan applicants
- **Route**: A linear road path connecting multiple barangays in a specific direction (e.g., "Bayawan → Kalumboyan → Border")
- **Barangay**: The smallest administrative division in the Philippines, equivalent to a village or district
- **Municipality**: A local government unit that contains multiple barangays
- **Application_Assignment_System**: The subsystem responsible for matching loan applications to CI staff based on geographic routes
- **Route_Configuration**: A data structure mapping barangays and municipalities to specific route names
- **Admin**: Administrative user with permissions to assign routes to CI staff
- **Loan_Staff**: Staff members who submit loan applications on behalf of applicants
- **Applicant_Location**: The barangay and municipality where a loan applicant resides

## Requirements

### Requirement 1: Route Assignment to CI Staff

**User Story:** As an admin, I want to assign one linear road route to each CI staff member, so that each CI has a defined geographic coverage area.

#### Acceptance Criteria

1. THE Admin_Interface SHALL display a route selection field when creating or editing CI staff accounts
2. THE System SHALL store the assigned route name in the users table for each CI staff member
3. THE System SHALL enforce that each CI staff member has exactly one assigned route
4. THE CI_Dashboard SHALL display the assigned route name for the logged-in CI staff member
5. WHEN an admin updates a CI staff member's assigned route, THE System SHALL update the database immediately

### Requirement 2: Route Configuration Management

**User Story:** As a system administrator, I want to define which barangays and municipalities belong to each route, so that the system can match applicant locations to routes.

#### Acceptance Criteria

1. THE Route_Configuration SHALL map each barangay to one or more route names
2. THE Route_Configuration SHALL support barangays that appear on multiple routes
3. THE Route_Configuration SHALL include all barangays from Bayawan City, Santa Catalina, and Basay municipalities
4. THE System SHALL provide example routes including "Bayawan → Kalumboyan → Border", "Bayawan → Candumao → Basay → Border", "Bayawan → Sipalay", and "Bayawan → Santa Catalina"
5. THE Route_Configuration SHALL be accessible to the Application_Assignment_System during application submission

### Requirement 3: Geographic Route-Based Assignment

**User Story:** As a loan staff member, I want applications to be automatically assigned to the CI staff covering that geographic route, so that CI staff can efficiently travel their routes without backtracking.

#### Acceptance Criteria

1. WHEN a loan application is submitted, THE Application_Assignment_System SHALL extract the barangay and municipality from the member_address field
2. WHEN the applicant location is extracted, THE Application_Assignment_System SHALL query the Route_Configuration to determine which route covers that location
3. WHEN a matching route is found, THE Application_Assignment_System SHALL assign the application to the CI staff member assigned to that route
4. IF no CI staff member is assigned to the matching route, THEN THE System SHALL leave the application unassigned and notify the admin
5. IF the applicant location does not match any configured route, THEN THE System SHALL leave the application unassigned and notify the admin
6. THE System SHALL update the assigned_ci_staff field in the loan_applications table with the matched CI staff member's ID
7. THE System SHALL update the application status to "assigned_to_ci" when successfully assigned

### Requirement 4: Database Schema Extension

**User Story:** As a developer, I want the database schema to support route assignments, so that route information can be persisted and queried efficiently.

#### Acceptance Criteria

1. THE users table SHALL include an assigned_route field of type TEXT
2. THE assigned_route field SHALL be nullable to support non-CI staff roles
3. THE System SHALL maintain backward compatibility with existing user records
4. WHEN a CI staff account is created, THE System SHALL allow the assigned_route field to be populated during signup
5. THE System SHALL support querying CI staff by assigned route name

### Requirement 5: Route Selection During Signup

**User Story:** As a new CI staff member, I want to select my assigned route during account registration, so that my route assignment is established from the beginning.

#### Acceptance Criteria

1. WHEN a user selects "ci_staff" as their role during signup, THE Signup_Form SHALL display a route selection dropdown
2. THE route selection dropdown SHALL include all available route names from the Route_Configuration
3. THE Signup_Form SHALL require route selection for CI staff roles
4. THE Signup_Form SHALL not display route selection for loan_staff or admin roles
5. WHEN the signup form is submitted, THE System SHALL store the selected route in the assigned_route field

### Requirement 6: Admin Route Management Interface

**User Story:** As an admin, I want to view and modify route assignments for existing CI staff, so that I can adjust coverage areas as needed.

#### Acceptance Criteria

1. THE Manage_Users_Interface SHALL display the assigned route for each CI staff member in the active users table
2. THE Manage_Users_Interface SHALL provide an edit action that allows admins to change a CI staff member's assigned route
3. WHEN an admin changes a CI staff member's route, THE System SHALL update the assigned_route field in the database
4. THE Manage_Users_Interface SHALL display "Not Assigned" for CI staff members without an assigned route
5. THE System SHALL allow admins to assign routes to CI staff who were created before this feature was implemented

### Requirement 7: CI Dashboard Route Display

**User Story:** As a CI staff member, I want to see my assigned route on my dashboard, so that I know which geographic area I am responsible for.

#### Acceptance Criteria

1. THE CI_Dashboard SHALL display the assigned route name prominently near the top of the page
2. THE CI_Dashboard SHALL display the list of barangays covered by the assigned route
3. IF a CI staff member has no assigned route, THEN THE CI_Dashboard SHALL display a message indicating "No route assigned - contact admin"
4. THE route display SHALL be visible on both desktop and mobile views

### Requirement 8: Address Parsing and Matching

**User Story:** As a system, I want to accurately parse applicant addresses and match them to routes, so that applications are assigned to the correct CI staff.

#### Acceptance Criteria

1. THE Application_Assignment_System SHALL parse the member_address field to extract barangay and municipality names
2. THE Application_Assignment_System SHALL handle address variations including different capitalization and spacing
3. THE Application_Assignment_System SHALL match barangay names case-insensitively
4. IF the address contains multiple barangays or municipalities, THEN THE System SHALL use the first valid match
5. THE System SHALL log parsing failures for admin review

### Requirement 9: Notification System Integration

**User Story:** As a CI staff member, I want to receive notifications when applications are assigned to my route, so that I can plan my field visits efficiently.

#### Acceptance Criteria

1. WHEN an application is assigned to a CI staff member via route matching, THE System SHALL create a notification for that CI staff member
2. THE notification SHALL include the applicant name and barangay location
3. THE notification SHALL include a link to the application details page
4. THE System SHALL maintain existing notification behavior for other application events

### Requirement 10: Backward Compatibility and Migration

**User Story:** As a system administrator, I want the system to handle existing CI staff and applications gracefully during the transition to route-based assignment, so that operations are not disrupted.

#### Acceptance Criteria

1. THE System SHALL continue to support CI staff members without assigned routes
2. WHEN a CI staff member has no assigned route, THE System SHALL fall back to the previous workload-based assignment logic
3. THE System SHALL allow admins to gradually assign routes to existing CI staff members
4. THE System SHALL not require immediate route assignment for all CI staff members
5. WHEN both route-based and workload-based CI staff exist, THE System SHALL prioritize route-based assignment when a matching route is found

