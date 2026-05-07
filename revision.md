# Revision History

## v1.0.9 - 5/7/2026

Merged Whitney duplicate records.

- Confirmed `Whitney, Dave` and `Whitney, David` are the same person.
- Added a confirmed Choir Genius alias mapping `Whitney, Dave` to canonical member `Whitney, David`.
- Preserved Dave Whitney's roster quartet assignment on David Whitney.
- Removed the duplicate `Whitney, Dave` database member record, keeping `Whitney, David` as the preferred entry.

## v1.0.8 - 5/7/2026

Added Choir Genius account import and data overwrite support.

- Added `member_external_account`, `member_emergency_contact`, `member_role`, and `member_role_assignment` tables.
- Added repeatable `scripts/import_choir_genius_accounts.py` importer.
- Imported the 161-row Choir Genius CSV export with CSV values taking precedence over generated roster data for matched members.
- Added support for Choir Genius member-since dates, birthdays, anniversaries, addresses, emails, phones, voice parts, spouse data, emergency contacts, dues dates, skills, account identifiers, classifications, and leadership roles.
- Displayed Choir Genius account data, emergency contacts, and leadership roles on member detail pages.

## v1.0.7 - 5/6/2026

Added database support for Choir Genius classifications.

- Added `member_classification` and `member_classification_assignment` tables.
- Modeled Choir Genius `Roles`, `Subgroups`, and `Labels` as external classifications.
- Kept external classifications separate from future internal leadership role history.
- Added classification display to member detail pages.
- Updated setup schema and migrations for fresh and existing databases.

## v1.0.6 - 5/6/2026

Added known Choir Genius name reconciliation.

- Added `data_reconciliation/name_aliases.csv`.
- Recorded that Choir Genius `Depret, Kate` maps to database member `Depret-Guillaume, Kate`.
- Marked the alias as user-confirmed so future imports should treat the records as the same person.

## v1.0.5 - 5/6/2026

Removed the separate Member Directory page.

- Removed the standalone `/members` roster page.
- Removed the Member Directory item from the sidebar.
- Made the dashboard roster the single member directory surface.
- Kept member detail, edit, and family management routes under `/members/{id}`.
- Updated dashboard roster controls and search fallbacks so they no longer point to the removed page.

## v1.0.4 - 5/6/2026

Improved roster category filter toggling.

- Made top roster category filters toggle off when clicked a second time.
- Restored the `Members` all-rows state when a selected category filter is cleared.
- Preserved search text while category filters are toggled on or off.

## v1.0.3 - 5/6/2026

Improved dashboard roster search behavior.

- Made the dashboard roster search filter rows reactively as text is entered.
- Made clearing the dashboard search box immediately restore the visible roster rows.
- Kept category filters and search text combined so clearing search preserves the active category filter.

## v1.0.2 - 5/6/2026

Added revision history tracking.

- Added `revision.md` as the project changelog.
- Established newest-first revision notes for each version tag.
- Clarified that `version.md` holds the current version and versioning rules.

## v1.0.1 - 5/6/2026

Added version display and independent name sorting.

- Added `version.md` with major.minor.revision versioning rules.
- Displayed the current version in small text at the bottom of the dashboard.
- Split the roster `Name` column into separate `Last` and `First` columns.
- Made `Last` and `First` independently sortable from the roster headers.
- Added Git tag `v1.0.1`.

## v1.0.0 - 4/5/2026

Baseline internal membership portal configuration and capabilities.

- Created the standalone Jubilaires Membership project separate from Farrlind.
- Added FastAPI/Jinja web application structure with a dedicated project `.venv`.
- Added PostgreSQL/Docker development database configuration.
- Imported the 2026 chapter membership roster from `ChapterMembership2026.docx`.
- Added member, family, voice part, quartet, address, phone, email, and status data foundations.
- Converted voice parts to many-to-many membership.
- Added one-to-many family records for spouses, children, parents, siblings, and other relationships.
- Converted years with group into membership start dates.
- Added member and family picture path support.
- Extracted embedded roster photos into static project storage.
- Added member detail, member edit, and family add/edit/delete workflows.
- Added a professional internal portal layout with sidebar navigation, header search, Fairfax Jubil-Aires logo, dashboard metrics, and roster table.
- Added dashboard/member roster search, category filters, and sortable table headers.
- Created the Git project baseline and added Git tag `v1.0.0`.
