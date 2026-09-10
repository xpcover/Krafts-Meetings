-- Krafts Meetings — Contact Management schema (SQLite)
-- Version 1
--
-- Flow: business card image -> vision extraction -> contact confirmation
--       -> SQLite (contacts / organizations / interactions / templates
--       -> email drafts / settings) -> AI email engine -> Gmail / Outlook
--
-- Requires SQLite >= 3.38 (unixepoch()) and the FTS5 extension.

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- ============================================================
-- SCHEMA VERSION
-- ============================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  INTEGER NOT NULL
);

INSERT OR IGNORE INTO schema_version (version, applied_at)
VALUES (1, unixepoch());


-- ============================================================
-- USERS
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id                  TEXT PRIMARY KEY,
    external_user_id    TEXT UNIQUE,

    email               TEXT,
    display_name        TEXT,

    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'inactive', 'deleted')),

    created_at          INTEGER NOT NULL,
    updated_at          INTEGER NOT NULL
);


-- ============================================================
-- USER PROFILE
-- Used as context when AI writes emails
-- ============================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    id                      TEXT PRIMARY KEY,
    user_id                 TEXT NOT NULL UNIQUE,

    full_name               TEXT,
    job_title               TEXT,
    company_name            TEXT,
    company_domain          TEXT,

    professional_summary    TEXT,
    email_signature         TEXT,

    communication_style     TEXT,

    profile_data            TEXT NOT NULL DEFAULT '{}'
                            CHECK (json_valid(profile_data)),

    created_at              INTEGER NOT NULL,
    updated_at              INTEGER NOT NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- ============================================================
-- ORGANIZATIONS / COMPANIES
-- ============================================================

CREATE TABLE IF NOT EXISTS organizations (
    id                  TEXT PRIMARY KEY,

    name                TEXT NOT NULL,

    domain              TEXT,
    website_url         TEXT,
    linkedin_url        TEXT,

    industry            TEXT,

    address             TEXT,
    city                TEXT,
    state               TEXT,
    country             TEXT,
    postal_code         TEXT,

    organization_data   TEXT NOT NULL DEFAULT '{}'
                        CHECK (json_valid(organization_data)),

    created_at          INTEGER NOT NULL,
    updated_at          INTEGER NOT NULL
);


CREATE INDEX IF NOT EXISTS idx_organizations_name
ON organizations(name COLLATE NOCASE);

CREATE INDEX IF NOT EXISTS idx_organizations_domain
ON organizations(domain COLLATE NOCASE);


-- ============================================================
-- CONTACTS
-- ============================================================

CREATE TABLE IF NOT EXISTS contacts (
    id                      TEXT PRIMARY KEY,

    user_id                 TEXT NOT NULL,
    organization_id         TEXT,

    first_name              TEXT,
    last_name               TEXT,
    full_name               TEXT NOT NULL,

    job_title               TEXT,

    email                   TEXT,
    phone                   TEXT,
    mobile                  TEXT,

    linkedin_url            TEXT,
    website_url             TEXT,

    address                 TEXT,
    city                    TEXT,
    state                   TEXT,
    country                 TEXT,
    postal_code             TEXT,

    industry                TEXT,

    notes                   TEXT,

    source                  TEXT NOT NULL DEFAULT 'business_card'
                            CHECK (
                                source IN (
                                    'business_card',
                                    'manual',
                                    'import',
                                    'chatgpt',
                                    'api',
                                    'other'
                                )
                            ),

    extraction_confidence   REAL
                            CHECK (
                                extraction_confidence IS NULL
                                OR (
                                    extraction_confidence >= 0
                                    AND extraction_confidence <= 1
                                )
                            ),

    uncertain_fields        TEXT NOT NULL DEFAULT '[]'
                            CHECK (json_valid(uncertain_fields)),

    custom_data             TEXT NOT NULL DEFAULT '{}'
                            CHECK (json_valid(custom_data)),

    first_contacted_at      INTEGER,
    last_contacted_at       INTEGER,
    next_follow_up_at       INTEGER,

    status                  TEXT NOT NULL DEFAULT 'active'
                            CHECK (
                                status IN (
                                    'active',
                                    'archived',
                                    'deleted'
                                )
                            ),

    created_at              INTEGER NOT NULL,
    updated_at              INTEGER NOT NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (organization_id)
        REFERENCES organizations(id)
        ON DELETE SET NULL
);


CREATE INDEX IF NOT EXISTS idx_contacts_user
ON contacts(user_id);

CREATE INDEX IF NOT EXISTS idx_contacts_name
ON contacts(user_id, full_name COLLATE NOCASE);

CREATE INDEX IF NOT EXISTS idx_contacts_email
ON contacts(user_id, email COLLATE NOCASE);

CREATE INDEX IF NOT EXISTS idx_contacts_organization
ON contacts(organization_id);

CREATE INDEX IF NOT EXISTS idx_contacts_followup
ON contacts(user_id, next_follow_up_at)
WHERE next_follow_up_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_status
ON contacts(user_id, status);


-- ============================================================
-- BUSINESS CARD CAPTURES
-- Original capture + AI extraction history
-- ============================================================

CREATE TABLE IF NOT EXISTS business_card_captures (
    id                      TEXT PRIMARY KEY,

    user_id                 TEXT NOT NULL,
    contact_id              TEXT,

    image_path              TEXT,
    image_hash              TEXT,

    captured_at             INTEGER NOT NULL,

    extraction_status       TEXT NOT NULL DEFAULT 'pending'
                            CHECK (
                                extraction_status IN (
                                    'pending',
                                    'processing',
                                    'completed',
                                    'failed',
                                    'rejected'
                                )
                            ),

    extracted_data          TEXT NOT NULL DEFAULT '{}'
                            CHECK (json_valid(extracted_data)),

    extraction_model        TEXT,

    extraction_confidence   REAL
                            CHECK (
                                extraction_confidence IS NULL
                                OR (
                                    extraction_confidence >= 0
                                    AND extraction_confidence <= 1
                                )
                            ),

    processing_error        TEXT,

    created_at              INTEGER NOT NULL,
    updated_at              INTEGER NOT NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (contact_id)
        REFERENCES contacts(id)
        ON DELETE SET NULL
);


CREATE INDEX IF NOT EXISTS idx_card_user
ON business_card_captures(user_id);

CREATE INDEX IF NOT EXISTS idx_card_contact
ON business_card_captures(contact_id);

CREATE INDEX IF NOT EXISTS idx_card_hash
ON business_card_captures(user_id, image_hash);


-- ============================================================
-- CONTACT INTERACTIONS
-- Meetings, calls, conferences, emails, notes etc.
-- ============================================================

CREATE TABLE IF NOT EXISTS contact_interactions (
    id                  TEXT PRIMARY KEY,

    user_id             TEXT NOT NULL,
    contact_id          TEXT NOT NULL,

    interaction_type    TEXT NOT NULL
                        CHECK (
                            interaction_type IN (
                                'business_card',
                                'meeting',
                                'call',
                                'email',
                                'linkedin',
                                'event',
                                'conference',
                                'introduction',
                                'note',
                                'other'
                            )
                        ),

    interaction_at      INTEGER NOT NULL,

    title               TEXT,
    summary             TEXT,
    notes               TEXT,
    location            TEXT,

    metadata            TEXT NOT NULL DEFAULT '{}'
                        CHECK (json_valid(metadata)),

    created_at          INTEGER NOT NULL,
    updated_at          INTEGER NOT NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (contact_id)
        REFERENCES contacts(id)
        ON DELETE CASCADE
);


CREATE INDEX IF NOT EXISTS idx_interactions_contact
ON contact_interactions(contact_id, interaction_at DESC);

CREATE INDEX IF NOT EXISTS idx_interactions_user
ON contact_interactions(user_id, interaction_at DESC);

CREATE INDEX IF NOT EXISTS idx_interactions_type
ON contact_interactions(user_id, interaction_type);


-- ============================================================
-- RELATIONSHIP STATE
-- Lifecycle: new_contact -> met -> conversation -> follow_up_required
--            -> meeting_scheduled -> opportunity -> customer_partner
--            -> dormant
-- ============================================================

CREATE TABLE IF NOT EXISTS contact_relationships (
    id                  TEXT PRIMARY KEY,

    contact_id          TEXT NOT NULL,

    relationship_type   TEXT NOT NULL,

    relationship_stage  TEXT NOT NULL DEFAULT 'new_contact'
                        CHECK (
                            relationship_stage IN (
                                'new_contact',
                                'met',
                                'conversation',
                                'follow_up_required',
                                'meeting_scheduled',
                                'opportunity',
                                'customer_partner',
                                'dormant'
                            )
                        ),

    relationship_status TEXT NOT NULL DEFAULT 'active'
                        CHECK (
                            relationship_status IN (
                                'active',
                                'inactive',
                                'dormant',
                                'closed'
                            )
                        ),

    priority            INTEGER NOT NULL DEFAULT 0
                        CHECK (priority BETWEEN 0 AND 5),

    context             TEXT,

    started_at          INTEGER,
    last_activity_at    INTEGER,
    next_action_at      INTEGER,

    metadata            TEXT NOT NULL DEFAULT '{}'
                        CHECK (json_valid(metadata)),

    created_at          INTEGER NOT NULL,
    updated_at          INTEGER NOT NULL,

    FOREIGN KEY (contact_id)
        REFERENCES contacts(id)
        ON DELETE CASCADE
);


CREATE INDEX IF NOT EXISTS idx_relationship_contact
ON contact_relationships(contact_id);

CREATE INDEX IF NOT EXISTS idx_relationship_next_action
ON contact_relationships(next_action_at);

CREATE INDEX IF NOT EXISTS idx_relationship_priority
ON contact_relationships(priority DESC);

CREATE INDEX IF NOT EXISTS idx_relationship_stage
ON contact_relationships(relationship_stage);


-- ============================================================
-- TAGS
-- ============================================================

CREATE TABLE IF NOT EXISTS tags (
    id              TEXT PRIMARY KEY,

    user_id         TEXT NOT NULL,

    name            TEXT NOT NULL,
    description     TEXT,

    created_at      INTEGER NOT NULL,
    updated_at      INTEGER NOT NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    UNIQUE(user_id, name)
);


CREATE TABLE IF NOT EXISTS contact_tags (
    contact_id      TEXT NOT NULL,
    tag_id          TEXT NOT NULL,

    created_at      INTEGER NOT NULL,

    PRIMARY KEY (contact_id, tag_id),

    FOREIGN KEY (contact_id)
        REFERENCES contacts(id)
        ON DELETE CASCADE,

    FOREIGN KEY (tag_id)
        REFERENCES tags(id)
        ON DELETE CASCADE
);


CREATE INDEX IF NOT EXISTS idx_contact_tags_tag
ON contact_tags(tag_id);


-- ============================================================
-- EMAIL OBJECTIVES
-- ============================================================

CREATE TABLE IF NOT EXISTS email_objectives (
    id                  TEXT PRIMARY KEY,

    user_id             TEXT,

    name                TEXT NOT NULL,
    description         TEXT,

    system_instructions TEXT,

    default_tone        TEXT,

    is_system           INTEGER NOT NULL DEFAULT 0
                        CHECK (is_system IN (0,1)),

    created_at          INTEGER NOT NULL,
    updated_at          INTEGER NOT NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


CREATE INDEX IF NOT EXISTS idx_email_objectives_user
ON email_objectives(user_id);


-- ============================================================
-- EMAIL TEMPLATES
-- ============================================================

CREATE TABLE IF NOT EXISTS email_templates (
    id                  TEXT PRIMARY KEY,

    user_id             TEXT,

    objective_id        TEXT,

    name                TEXT NOT NULL,
    description         TEXT,

    tone                TEXT,

    subject_template    TEXT,
    body_template       TEXT,

    template_data       TEXT NOT NULL DEFAULT '{}'
                        CHECK (json_valid(template_data)),

    is_system           INTEGER NOT NULL DEFAULT 0
                        CHECK (is_system IN (0,1)),

    created_at          INTEGER NOT NULL,
    updated_at          INTEGER NOT NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (objective_id)
        REFERENCES email_objectives(id)
        ON DELETE SET NULL
);


CREATE INDEX IF NOT EXISTS idx_templates_user
ON email_templates(user_id);

CREATE INDEX IF NOT EXISTS idx_templates_objective
ON email_templates(objective_id);


-- ============================================================
-- GENERATED EMAILS
-- ============================================================

CREATE TABLE IF NOT EXISTS generated_emails (
    id                  TEXT PRIMARY KEY,

    user_id             TEXT NOT NULL,

    contact_id          TEXT,
    interaction_id      TEXT,

    objective_id        TEXT,
    template_id         TEXT,

    recipient_email     TEXT,

    subject             TEXT,
    body                TEXT,

    generation_context  TEXT NOT NULL DEFAULT '{}'
                        CHECK (json_valid(generation_context)),

    model_name          TEXT,

    status              TEXT NOT NULL DEFAULT 'draft'
                        CHECK (
                            status IN (
                                'draft',
                                'edited',
                                'copied',
                                'sent',
                                'discarded'
                            )
                        ),

    generated_at        INTEGER NOT NULL,
    sent_at             INTEGER,

    created_at          INTEGER NOT NULL,
    updated_at          INTEGER NOT NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (contact_id)
        REFERENCES contacts(id)
        ON DELETE SET NULL,

    FOREIGN KEY (interaction_id)
        REFERENCES contact_interactions(id)
        ON DELETE SET NULL,

    FOREIGN KEY (objective_id)
        REFERENCES email_objectives(id)
        ON DELETE SET NULL,

    FOREIGN KEY (template_id)
        REFERENCES email_templates(id)
        ON DELETE SET NULL
);


CREATE INDEX IF NOT EXISTS idx_generated_email_contact
ON generated_emails(contact_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_generated_email_user
ON generated_emails(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_generated_email_status
ON generated_emails(user_id, status);


-- ============================================================
-- APP SETTINGS
-- ============================================================

CREATE TABLE IF NOT EXISTS app_settings (
    id                          TEXT PRIMARY KEY,

    user_id                     TEXT NOT NULL UNIQUE,

    default_email_tone          TEXT NOT NULL DEFAULT 'professional',

    default_email_length        TEXT NOT NULL DEFAULT 'medium',

    auto_save_contacts          INTEGER NOT NULL DEFAULT 1
                                CHECK (auto_save_contacts IN (0,1)),

    require_contact_confirmation INTEGER NOT NULL DEFAULT 1
                                CHECK (require_contact_confirmation IN (0,1)),

    require_email_confirmation  INTEGER NOT NULL DEFAULT 1
                                CHECK (require_email_confirmation IN (0,1)),

    settings_data               TEXT NOT NULL DEFAULT '{}'
                                CHECK (json_valid(settings_data)),

    created_at                  INTEGER NOT NULL,
    updated_at                  INTEGER NOT NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- ============================================================
-- AUDIT LOG
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id              TEXT PRIMARY KEY,

    user_id         TEXT,

    entity_type     TEXT NOT NULL,
    entity_id       TEXT,

    action          TEXT NOT NULL,

    metadata        TEXT NOT NULL DEFAULT '{}'
                    CHECK (json_valid(metadata)),

    created_at      INTEGER NOT NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE SET NULL
);


CREATE INDEX IF NOT EXISTS idx_audit_user
ON audit_logs(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_entity
ON audit_logs(entity_type, entity_id);


-- ============================================================
-- FULL TEXT SEARCH
-- ============================================================

CREATE VIRTUAL TABLE IF NOT EXISTS contacts_fts
USING fts5(
    contact_id UNINDEXED,
    full_name,
    job_title,
    email,
    phone,
    company_name,
    industry,
    notes,
    tokenize = 'unicode61'
);


-- ============================================================
-- FTS TRIGGERS
-- ============================================================

CREATE TRIGGER IF NOT EXISTS contacts_fts_insert
AFTER INSERT ON contacts
BEGIN
    INSERT INTO contacts_fts (
        contact_id,
        full_name,
        job_title,
        email,
        phone,
        company_name,
        industry,
        notes
    )
    SELECT
        NEW.id,
        NEW.full_name,
        NEW.job_title,
        NEW.email,
        NEW.phone,
        COALESCE(
            (SELECT name
             FROM organizations
             WHERE id = NEW.organization_id),
            ''
        ),
        NEW.industry,
        NEW.notes;
END;


CREATE TRIGGER IF NOT EXISTS contacts_fts_delete
AFTER DELETE ON contacts
BEGIN
    DELETE FROM contacts_fts
    WHERE contact_id = OLD.id;
END;


CREATE TRIGGER IF NOT EXISTS contacts_fts_update
AFTER UPDATE ON contacts
BEGIN

    DELETE FROM contacts_fts
    WHERE contact_id = OLD.id;

    INSERT INTO contacts_fts (
        contact_id,
        full_name,
        job_title,
        email,
        phone,
        company_name,
        industry,
        notes
    )
    SELECT
        NEW.id,
        NEW.full_name,
        NEW.job_title,
        NEW.email,
        NEW.phone,
        COALESCE(
            (SELECT name
             FROM organizations
             WHERE id = NEW.organization_id),
            ''
        ),
        NEW.industry,
        NEW.notes;
END;


-- Keep the denormalised company_name in FTS aligned when an
-- organization is renamed.
CREATE TRIGGER IF NOT EXISTS organizations_fts_rename
AFTER UPDATE OF name ON organizations
BEGIN
    UPDATE contacts_fts
    SET company_name = NEW.name
    WHERE contact_id IN (
        SELECT id FROM contacts WHERE organization_id = NEW.id
    );
END;


-- ============================================================
-- SYSTEM EMAIL OBJECTIVES
-- ============================================================

INSERT OR IGNORE INTO email_objectives (
    id,
    user_id,
    name,
    description,
    default_tone,
    is_system,
    created_at,
    updated_at
)
VALUES
(
    'objective-follow-up',
    NULL,
    'Follow Up',
    'Follow up after meeting or initial interaction',
    'professional',
    1,
    unixepoch(),
    unixepoch()
),
(
    'objective-introduction',
    NULL,
    'Introduction',
    'Introduce the sender or their company',
    'professional',
    1,
    unixepoch(),
    unixepoch()
),
(
    'objective-sales',
    NULL,
    'Sales',
    'Introduce a product or service and explore an opportunity',
    'consultative',
    1,
    unixepoch(),
    unixepoch()
),
(
    'objective-partnership',
    NULL,
    'Partnership',
    'Explore a potential business partnership',
    'professional',
    1,
    unixepoch(),
    unixepoch()
),
(
    'objective-meeting',
    NULL,
    'Meeting Request',
    'Request a meeting or call',
    'concise',
    1,
    unixepoch(),
    unixepoch()
),
(
    'objective-thank-you',
    NULL,
    'Thank You',
    'Thank the contact after a meeting or introduction',
    'warm',
    1,
    unixepoch(),
    unixepoch()
),
(
    'objective-information',
    NULL,
    'Send Information',
    'Share requested information or material',
    'professional',
    1,
    unixepoch(),
    unixepoch()
);


-- ============================================================
-- DEFAULT RELATIONSHIP TYPES
-- ============================================================

-- Stored in application configuration rather than a separate
-- table because these are controlled vocabulary values.

COMMIT;
