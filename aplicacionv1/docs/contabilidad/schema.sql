-- Esquema de referencia PostgreSQL. Para migrar una base existente: make migrate.
-- No sustituye las migraciones Alembic ni los datos originales.
CREATE EXTENSION IF NOT EXISTS vector;


CREATE TABLE areas (
	id SERIAL NOT NULL, 
	code VARCHAR(255) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;


CREATE TABLE audit_logs (
	id SERIAL NOT NULL, 
	user_id VARCHAR(36), 
	action VARCHAR(100) NOT NULL, 
	resource_type VARCHAR(100) NOT NULL, 
	resource_id VARCHAR(100), 
	payload_json JSON NOT NULL, 
	ip VARCHAR(60), 
	status VARCHAR(30) NOT NULL, 
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);


CREATE TABLE data_dictionary (
	id SERIAL NOT NULL, 
	termino_usuario VARCHAR(150) NOT NULL, 
	columna_canonica VARCHAR(150) NOT NULL, 
	tabla_origen VARCHAR(150) NOT NULL, 
	descripcion TEXT NOT NULL, 
	sinonimos_json JSON NOT NULL, 
	version INTEGER NOT NULL, 
	activo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (termino_usuario)
)

;


CREATE TABLE exchange_rates (
	id SERIAL NOT NULL, 
	date DATE NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	rate NUMERIC(20, 2) NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE financiadores (
	id SERIAL NOT NULL, 
	code VARCHAR(255) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;


CREATE TABLE gestiones (
	year SERIAL NOT NULL, 
	source_name VARCHAR(255) NOT NULL, 
	source_sha256 VARCHAR(64) NOT NULL, 
	imported_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (year)
)

;


CREATE TABLE import_logs (
	id SERIAL NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	source_name VARCHAR(255) NOT NULL, 
	rows INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (sha256)
)

;


CREATE TABLE knowledge_chunks (
	id VARCHAR(36) NOT NULL, 
	content TEXT NOT NULL, 
	content_tokens INTEGER NOT NULL, 
	embedding VECTOR(1024) NOT NULL, 
	source_type VARCHAR(40) NOT NULL, 
	source_id VARCHAR(255) NOT NULL, 
	source_title VARCHAR(500) NOT NULL, 
	chunk_index INTEGER NOT NULL, 
	tags JSON NOT NULL, 
	metadata_json JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (source_id, chunk_index)
)

;

CREATE INDEX ix_knowledge_chunks_source_type ON knowledge_chunks (source_type);

CREATE INDEX ix_knowledge_embedding_hnsw ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX ix_knowledge_chunks_source_id ON knowledge_chunks (source_id);


CREATE TABLE ledger_accounts (
	id SERIAL NOT NULL, 
	code VARCHAR(50) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	parent_id INTEGER, 
	kind VARCHAR(30) NOT NULL, 
	section VARCHAR(100) NOT NULL, 
	liquidity_order INTEGER NOT NULL, 
	is_cash BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code), 
	FOREIGN KEY(parent_id) REFERENCES ledger_accounts (id)
)

;


CREATE TABLE oidc_transactions (
	state_hash VARCHAR(64) NOT NULL, 
	verifier VARCHAR(128) NOT NULL, 
	nonce VARCHAR(128) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (state_hash)
)

;


CREATE TABLE regiones (
	id SERIAL NOT NULL, 
	code VARCHAR(255) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;


CREATE TABLE rubros (
	id SERIAL NOT NULL, 
	code VARCHAR(255) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;


CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	full_name VARCHAR(180) NOT NULL, 
	oidc_subject VARCHAR(500), 
	password_hash VARCHAR(500), 
	role VARCHAR(30) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	region_ids JSON, 
	area_ids JSON, 
	financier_ids JSON, 
	PRIMARY KEY (id), 
	UNIQUE (email), 
	UNIQUE (oidc_subject)
)

;


CREATE TABLE auth_sessions (
	token_hash VARCHAR(64) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (token_hash), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id);


CREATE TABLE chat_sessions (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE INDEX ix_chat_sessions_user_id ON chat_sessions (user_id);


CREATE TABLE cuentas (
	id SERIAL NOT NULL, 
	code VARCHAR(255) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	rubro_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name, rubro_id), 
	FOREIGN KEY(rubro_id) REFERENCES rubros (id)
)

;


CREATE TABLE curation_batches (
	sha256 VARCHAR(64) NOT NULL, 
	id SERIAL NOT NULL, 
	owner_id VARCHAR(36) NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (owner_id, sha256), 
	FOREIGN KEY(owner_id) REFERENCES users (id)
)

;

CREATE INDEX ix_curation_batches_owner_id ON curation_batches (owner_id);


CREATE TABLE financial_disclosures (
	id SERIAL NOT NULL, 
	year INTEGER NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	account_id INTEGER, 
	title VARCHAR(255) NOT NULL, 
	body TEXT NOT NULL, 
	risk VARCHAR(20) NOT NULL, 
	author_id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(account_id) REFERENCES ledger_accounts (id), 
	FOREIGN KEY(author_id) REFERENCES users (id)
)

;

CREATE INDEX ix_financial_disclosures_year ON financial_disclosures (year);


CREATE TABLE journal_entries (
	id SERIAL NOT NULL, 
	date DATE NOT NULL, 
	description TEXT NOT NULL, 
	reference VARCHAR(100) NOT NULL, 
	entry_type VARCHAR(30) NOT NULL, 
	equity_event VARCHAR(40) NOT NULL, 
	author_id VARCHAR(36) NOT NULL, 
	reason TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (reference), 
	FOREIGN KEY(author_id) REFERENCES users (id)
)

;

CREATE INDEX ix_journal_entries_date ON journal_entries (date);


CREATE TABLE budgets (
	initial_amount NUMERIC(20, 2) NOT NULL, 
	id SERIAL NOT NULL, 
	year INTEGER NOT NULL, 
	month INTEGER NOT NULL, 
	region_id INTEGER NOT NULL, 
	area_id INTEGER NOT NULL, 
	financier_id INTEGER NOT NULL, 
	cuenta_id INTEGER NOT NULL, 
	source_row INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (year, source_row), 
	FOREIGN KEY(year) REFERENCES gestiones (year), 
	FOREIGN KEY(region_id) REFERENCES regiones (id), 
	FOREIGN KEY(area_id) REFERENCES areas (id), 
	FOREIGN KEY(financier_id) REFERENCES financiadores (id), 
	FOREIGN KEY(cuenta_id) REFERENCES cuentas (id)
)

;

CREATE INDEX ix_budgets_financier_id ON budgets (financier_id);

CREATE INDEX ix_budgets_region_id ON budgets (region_id);

CREATE INDEX ix_budgets_year ON budgets (year);

CREATE INDEX ix_budgets_cuenta_id ON budgets (cuenta_id);

CREATE INDEX ix_budgets_area_id ON budgets (area_id);

CREATE INDEX ix_budgets_month ON budgets (month);


CREATE TABLE chat_messages (
	id SERIAL NOT NULL, 
	session_id VARCHAR(36) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	content_json JSON NOT NULL, 
	sequence INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (session_id, sequence), 
	FOREIGN KEY(session_id) REFERENCES chat_sessions (id)
)

;

CREATE INDEX ix_chat_messages_session_id ON chat_messages (session_id);


CREATE TABLE conversation_contexts (
	session_id VARCHAR(36) NOT NULL, 
	active_filters_json JSON NOT NULL, 
	current_report VARCHAR(100), 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (session_id), 
	FOREIGN KEY(session_id) REFERENCES chat_sessions (id)
)

;


CREATE TABLE curation_rows (
	id SERIAL NOT NULL, 
	batch_id INTEGER NOT NULL, 
	source_row INTEGER NOT NULL, 
	original JSON NOT NULL, 
	data JSON NOT NULL, 
	issues JSON NOT NULL, 
	prediction JSON NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	version INTEGER NOT NULL, 
	validated_by VARCHAR(36), 
	validated_at TIMESTAMP WITH TIME ZONE, 
	target_kind VARCHAR(20), 
	target_id INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (batch_id, source_row), 
	FOREIGN KEY(batch_id) REFERENCES curation_batches (id), 
	FOREIGN KEY(validated_by) REFERENCES users (id)
)

;

CREATE INDEX ix_curation_rows_status ON curation_rows (status);

CREATE INDEX ix_curation_rows_batch_id ON curation_rows (batch_id);

CREATE INDEX ix_curation_rows_target_id ON curation_rows (target_id);


CREATE TABLE journal_lines (
	id SERIAL NOT NULL, 
	entry_id INTEGER NOT NULL, 
	account_id INTEGER NOT NULL, 
	debit NUMERIC(20, 2) NOT NULL, 
	credit NUMERIC(20, 2) NOT NULL, 
	cash_activity VARCHAR(20), 
	PRIMARY KEY (id), 
	CONSTRAINT ck_journal_one_side CHECK (debit >= 0 AND credit >= 0 AND (debit = 0 OR credit = 0)), 
	FOREIGN KEY(entry_id) REFERENCES journal_entries (id), 
	FOREIGN KEY(account_id) REFERENCES ledger_accounts (id)
)

;

CREATE INDEX ix_journal_lines_entry_id ON journal_lines (entry_id);

CREATE INDEX ix_journal_lines_account_id ON journal_lines (account_id);


CREATE TABLE movements (
	date DATE NOT NULL, 
	amount NUMERIC(20, 2) NOT NULL, 
	reference VARCHAR(255) NOT NULL, 
	description TEXT NOT NULL, 
	accounting_code VARCHAR(255) NOT NULL, 
	movement_type VARCHAR(40) NOT NULL, 
	original_data JSON NOT NULL, 
	id SERIAL NOT NULL, 
	year INTEGER NOT NULL, 
	month INTEGER NOT NULL, 
	region_id INTEGER NOT NULL, 
	area_id INTEGER NOT NULL, 
	financier_id INTEGER NOT NULL, 
	cuenta_id INTEGER NOT NULL, 
	source_row INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (year, source_row), 
	FOREIGN KEY(year) REFERENCES gestiones (year), 
	FOREIGN KEY(region_id) REFERENCES regiones (id), 
	FOREIGN KEY(area_id) REFERENCES areas (id), 
	FOREIGN KEY(financier_id) REFERENCES financiadores (id), 
	FOREIGN KEY(cuenta_id) REFERENCES cuentas (id)
)

;

CREATE INDEX ix_movements_area_id ON movements (area_id);

CREATE INDEX ix_movements_year ON movements (year);

CREATE INDEX ix_movements_cuenta_id ON movements (cuenta_id);

CREATE INDEX ix_movements_region_id ON movements (region_id);

CREATE INDEX ix_movements_date ON movements (date);

CREATE INDEX ix_movements_financier_id ON movements (financier_id);

CREATE INDEX ix_movements_month ON movements (month);


CREATE TABLE budget_modifications (
	id SERIAL NOT NULL, 
	budget_id INTEGER NOT NULL, 
	amount NUMERIC(20, 2) NOT NULL, 
	date DATE NOT NULL, 
	description TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(budget_id) REFERENCES budgets (id)
)

;

CREATE INDEX ix_budget_modifications_budget_id ON budget_modifications (budget_id);