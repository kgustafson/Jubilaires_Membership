# Revision History

## v1.0.40 - 5/7/2026

Normalized quartet contact phone display.

- Formatted standard 10-digit phone numbers as `(XXX) XXX-XXXX`.
- Accepted leading `1` country-code numbers and displayed them in the same local format.
- Left non-standard phone numbers unchanged.

## v1.0.39 - 5/7/2026

Refined quartet contact phone labels.

- Added compact phone type prefixes in quartet contact modals.
- Displayed cell/mobile as `C`, home as `H`, and work/office as `O`.

## v1.0.38 - 5/7/2026

Restyled quartet contact modals.

- Reworked quartet member contact modals into a simple address-card layout.
- Showed the member name at 14pt, followed by an optional photo.
- Bolded phone numbers and email addresses and formatted mailing addresses with line breaks.
- Removed contact-label prefixes from phone and email values.
- Split mailing addresses into street, optional second line, city/state, and ZIP lines.

## v1.0.37 - 5/7/2026

Simplified quartet member rows.

- Removed inline member thumbnails from quartet member listings.
- Kept member photos in the contact detail modal.
- Left-aligned the clickable member name in quartet member rows.

## v1.0.36 - 5/7/2026

Added quartet member contact previews.

- Added member profile thumbnails to quartet member rows.
- Made quartet member names open contact summary modals.
- Included phone numbers, emails, mailing addresses, and member voice parts in the quartet contact modal.

## v1.0.35 - 5/7/2026

Trimmed quartet photo padding before resizing.

- Added uniform border trimming before quartet photo cover-crop resizing.
- Reprocessed existing quartet photos so image content fills the allocated 2000x1600 frame instead of sitting inside old padding.

## v1.0.34 - 5/7/2026

Cleaned roster navigation.

- Removed Attendance Tracking from the side menu.
- Removed Dues Tracking from the side menu.

## v1.0.33 - 5/7/2026

Fixed quartet photo frame-fill resizing.

- Changed quartet photo normalization from fit-with-padding to cover-and-crop.
- Reprocessed the Just Four Grins quartet image from the uploaded source photo so it fills the 2000x1600 quartet frame.

## v1.0.32 - 5/7/2026

Fixed Quartet Management add-member modal search.

- Changed the add-member modal title to include the quartet name.
- Replaced unreliable hidden-option filtering with a select list that rebuilds visible member options as the search changes.

## v1.0.31 - 5/7/2026

Adjusted Quartet Management card layout.

- Made quartet cards wider for member list readability.
- Stabilized quartet action button height so cards without photos do not stretch buttons.
- Aligned member names, quartet parts, edit controls, and remove controls on a single row.
- Normalized existing quartet photos to the standard 2000x1600 size.

## v1.0.30 - 5/7/2026

Refined Quartet Management member workflows and photo sizing.

- Changed quartet member display to a primary-then-alternate list.
- Added per-member edit and remove controls on quartet cards.
- Changed the quartet Members action into Add Member with a searchable member selector modal.
- Kept add/edit controls collecting quartet part and primary/alternate state.
- Updated quartet photo normalization to upscale smaller uploads to the standard 2000x1600 size.

## v1.0.29 - 5/7/2026

Added quartet-specific voice parts.

- Added a `voice_part_id` field to quartet membership assignments.
- Updated Quartet Management membership editing to collect primary/alternate state and the part sung in that quartet.
- Kept quartet voice parts independent from each member's general voice-part profile.
- Displayed assigned quartet parts on quartet cards.

## v1.0.28 - 5/7/2026

Added quartet management.

- Added a Quartet Management page with quartet creation, editing, deletion, and membership editing by quartet.
- Allowed administrators and primary members of a quartet to modify that quartet.
- Added quartet photo storage with larger 10x8 group photo normalization.
- Added a quartet photo database column and migration.

## v1.0.27 - 5/7/2026

Added database backup and recovery administration.

- Added an administrator-only Database page.
- Added one-click PostgreSQL backups stored in `backups/` using `YYYY-MM-DD-XXX.dump` names with daily ordinal increments.
- Added recovery from an existing saved backup or an uploaded backup file selected through a file picker.
- Added restore confirmation modals and backup/recovery status messaging.

## v1.0.26 - 5/7/2026

Fixed default inactive row visibility on the dashboard.

- Added server-rendered hidden state for non-active roster rows so inactive members do not appear before dashboard filtering JavaScript runs.
- Kept the Show Inactive checkbox able to reveal inactive members through the existing roster filter behavior.

## v1.0.25 - 5/7/2026

Changed dashboard roster active/inactive filtering.

- Made the dashboard default to showing active members only.
- Removed the Active metric card and made Members a passive count instead of a clickable filter.
- Added a Show Inactive checkbox near the roster count.
- Made Members, Tenor, Lead, Baritone, and Bass counts update when Show Inactive changes.
- Kept part metric filtering scoped to active members unless Show Inactive is checked.

## v1.0.24 - 5/7/2026

Added administrator two-factor authentication.

- Added Google Authenticator compatible TOTP setup for administrator accounts.
- Required administrator accounts to complete TOTP setup or verification after password login.
- Added one-time recovery codes stored as password-style hashes.
- Added administrator reset controls for another administrator's two-factor setup.
- Added TOTP and QR-code dependencies for local, no-SMS two-factor authentication.

## v1.0.23 - 5/7/2026

Tightened account and member edit permissions.

- Added username editing to the account information page with duplicate username validation.
- Added member edit authorization so non-admin users can only edit the member record linked to their login.
- Hid member edit, family edit, family remove, and add-family controls from member records the current user cannot edit.

## v1.0.22 - 5/7/2026

Added account profile access from the header.

- Added last-login tracking for application users.
- Added a header account link that opens the current user's account information form.
- Added account self-service editing for first name, last name, email, and password changes.
- Updated Authentication todo items for last-login display, account profile, and self-service password changes.

## v1.0.21 - 5/7/2026

Updated inactive member classification rules.

- Added a migration to mark members inactive when Choir Genius has role `Applicant` or subgroup `Former`.
- Preserved existing inactive dates and filled missing inactive dates with the migration date.

## v1.0.20 - 5/7/2026

Reorganized authentication planning.

- Moved login, logout, user account, and role/permission todo items into a dedicated Authentication section.
- Added a future Authentication todo item for two-factor authentication using Google Authenticator.

## v1.0.19 - 5/7/2026

Added login, registration, and user administration.

- Added an `app_user` table with member links, unique email/username checks, password hashes, and role approval state.
- Added login, logout, and registration pages.
- Added the session signing dependency required by the login session middleware.
- Made new registrations pending until an administrator assigns member or administrator access.
- Added a User Administration page for approving pending registrations.
- Added administrator roster controls for member deletion confirmation and password changes.
- Added a bootstrap script for creating or updating the initial administrator account.

## v1.0.18 - 5/7/2026

Removed legacy derived date fields from the roster model.

- Added a migration to drop legacy `years_with_group`, birthday month/day, and spouse birthday month/day columns.
- Retired old initialization logic that referenced legacy birthday and years-with-group columns.
- Replaced the dashboard roster Start column with derived Years Active.
- Calculated Years Active from start date to inactive date for inactive members, or to the current date for active members.
- Added numeric sorting support for the derived Years Active roster column.

## v1.0.17 - 5/7/2026

Expanded Photo Review assignment management.

- Changed Photo Review to show all roster photos, including already assigned photos.
- Added assignment status labels for member and family photo assignments.
- Preselected the current member or family target in each photo assignment form.
- Added Photo Review remove-assignment controls for assigned photos.
- Updated reassignment saves to clear any previous owner before assigning the selected photo.

## v1.0.16 - 5/7/2026

Improved photo assignment safeguards.

- Hid photos already assigned to another member or family record from photo picker choices.
- Kept the current person's assigned photo visible while editing that person.
- Added remove-current-photo controls for member and family photo dialogs.
- Added backend checks so selected existing photos cannot be assigned to multiple people.

## v1.0.15 - 5/7/2026

Normalized roster photos.

- Added a repeatable one-time script to normalize extracted roster photos.
- Converted 95 roster photos to 512x512 JPEG files under `static/photos/roster`.
- Updated the photo manifest to point at the normalized JPEG files while retaining original source paths.
- Limited photo picker choices to manifest-backed roster photos and profile uploads.
- Updated the todo list to show roster photo normalization as complete.

## v1.0.14 - 5/7/2026

Added member and family photo management.

- Added Pillow-backed profile photo processing that stores uploaded photos as 512x512 JPEG images.
- Added reusable photo picker modals with file selection, drag/drop, clipboard paste, preview, and existing-photo selection.
- Added member and family photo upload/select controls.
- Added a Photo Review page for unassigned roster photos with assignment controls for members and family records.
- Updated the sidebar and todo list for the new photo review workflow.

## v1.0.13 - 5/7/2026

Added image processing dependency for photo workflows.

- Installed Pillow in the dedicated project `.venv`.
- Added Pillow to `requirements.txt` so upload resizing and thumbnail generation are reproducible.
- Verified Pillow can read an existing roster photo from `static/photos`.

## v1.0.12 - 5/7/2026

Added modal role and contact editors.

- Added a member role assignment modal with role selection, start dates, end dates, and notes.
- Added modal editors for member email, phone, and address rows.
- Wired member edit saves to persist role assignments and contact records from the modal workflow.
- Updated the todo list to show the completed role, address, phone, and email editor work.

## v1.0.11 - 5/7/2026

Added member voice part and quartet editors.

- Added quartet lifecycle fields: active state, formation date, and deactivation date.
- Added a member edit voice part multi-select editor.
- Added quartet membership editing with primary/alternate assignment state.
- Added quartet lifecycle editing from the member edit workflow.
- Updated member detail pages to show quartet active/inactive and lifecycle dates.

## v1.0.10 - 5/7/2026

Added database recovery planning.

- Added an Operations todo item to create a database recovery-from-backup workflow.

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

## v1.0.0 - 5/5/2026

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
