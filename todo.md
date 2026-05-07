# Jubilaires Membership Todo

## Data Model

- [x] Create member database project with FastAPI/Jinja web front end.
- [x] Import members from `ChapterMembership2026.docx`.
- [x] Add one-to-many family table for spouse, partner, children, parents, siblings, and other family.
- [x] Move family birthdays onto `member_family`.
- [x] Convert voice parts to many-to-many so members can sing multiple parts.
- [x] Convert years-with-group into `membership_start_date` using `2025 - years`.
- [x] Add member date fields: start date, inactive date, date of birth, date of death, anniversary date.
- [x] Add primary/alternate state for quartet membership.
- [x] Add picture path fields for members and family.
- [x] Add external classification tables for Choir Genius roles, subgroups, and labels.
- [ ] Add quartet lifecycle fields: active/inactive state, formation date, and deactivation date.
- [ ] Add member roles table for offices and jobs such as president, vice president, co-director, uniform chair, etc.
- [x] Add member roles table for offices and jobs such as president, vice president, co-director, uniform chair, etc.
- [x] Add many-to-many member role assignments with start date and end date so role history can be tracked over time.

## Import Cleanup

- [x] Fix address import.
- [x] Fix quartet import.
- [x] Extract embedded roster photos into `static/photos`.
- [ ] Review imported family records and correct spouse/child/other relationships.
- [x] Parse member birthday and anniversary values from Choir Genius exports.
- [ ] Decide when to drop legacy columns such as `years_with_group`, `birthday_month`, and spouse birthday fields from the live DB.

## Web Interface

- [ ] Add login/logout capability.
- [ ] Add user account table linked to members.
- [ ] Add roles/permissions: member and administrator.
- [ ] Build member self-service flow so logged-in members can update their own profile, family, contact info, and photos.
- [ ] Build administrator workflows with permission to change anything in the database.
- [x] Build member edit form.
- [x] Build family add/edit/delete workflow.
- [ ] Build voice part multi-select editor.
- [ ] Build quartet membership editor with primary/alternate selector.
- [ ] Build quartet editor for active/inactive state, formation date, and deactivation date.
- [ ] Build member role assignment editor with start/end dates.
- [ ] Build address editor.
- [ ] Build phone/email editor.
- [x] Add sorting and filtering to the roster view.
- [x] Change dashboard member table to include sortable/filterable controls on each column header.
- [x] Make dashboard metric cards clickable filters: Members, Active, Tenor, Lead, Baritone, Bass should filter the roster table when clicked.
- [x] Add a prominent search feature at the top of the dashboard.
- [ ] Add member and family photo upload/select controls.
- [ ] Add unassigned roster photo review page.

## Views And Reports

- [ ] Active roster view.
- [ ] Inactive/former roster view.
- [ ] Birthday and anniversary calendar.
- [ ] Quartet directory.
- [ ] Voice part balance report.
- [ ] Email list export.
- [ ] Phone list export.
- [ ] Printable/PDF roster export.

## Operations

- [x] Create Git repository for managing project changes.
- [ ] Tag each versioned Git change with its major.minor.revision number.
- [x] Create a dedicated `.venv` for this project and stop using any shared/Farrlind Python environment.
- [ ] Verify no runtime paths, services, credentials, Docker resources, media storage, backups, or deployment scripts depend on Farrlind or any other project.
- [ ] Add database backup script.
- [ ] Add web smoke tests.
- [ ] Containerize the membership application.
- [ ] Plan migration to AWS web services.
- [ ] Choose AWS deployment architecture for web app, database, static/media files, backups, and secrets.
- [ ] Prepare production deployment checklist for AWS.
