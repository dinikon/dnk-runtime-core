"""Lead, единый Deal, Basket и Funnel; одна воронка, без автоматизаций."""

from alembic import op

revision = "0002_crm_sales_mvp"
down_revision = "0001_tenant_baseline"
branch_labels = None
depends_on = None
DDL = (
    "\nCREATE TABLE crm_baskets (\n\tid UUID NOT NULL, \n\towner_model_key VARCHAR(32) NOT NULL, \n\towner_record_id UUID NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\ttotal NUMERIC(40, 2) NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\trevision INTEGER NOT NULL, \n\tsource_basket_id UUID, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_crm_basket_owner UNIQUE (owner_model_key, owner_record_id), \n\tCONSTRAINT ck_crm_basket_currency CHECK (currency IN ('USD','EUR','UAH')), \n\tCONSTRAINT ck_crm_basket_state CHECK (state IN ('editable','frozen') AND revision>0), \n\tFOREIGN KEY(source_basket_id) REFERENCES crm_baskets (id) ON DELETE SET NULL\n)\n\n",
    "\nCREATE TABLE funnels (\n\tmodel_key VARCHAR(32) NOT NULL, \n\tname VARCHAR(150) NOT NULL, \n\tis_default BOOLEAN NOT NULL, \n\trevision INTEGER NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_by UUID NOT NULL, \n\tupdated_by UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_funnels_model_key CHECK (model_key IN ('crm.lead','crm.deal')), \n\tCONSTRAINT ck_funnels_revision CHECK (revision>0)\n)\n\n",
    "CREATE UNIQUE INDEX uq_funnels_default ON funnels (model_key) WHERE is_default",
    "\nCREATE TABLE funnel_stages (\n\tid UUID NOT NULL, \n\tfunnel_id UUID NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\tcolor VARCHAR(7) NOT NULL, \n\tkind VARCHAR(16) NOT NULL, \n\tposition INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_funnel_stage_owner UNIQUE (funnel_id, id), \n\tCONSTRAINT uq_funnel_stage_position UNIQUE (funnel_id, position) DEFERRABLE INITIALLY DEFERRED, \n\tCONSTRAINT ck_funnel_stage_position CHECK (position>=0), \n\tCONSTRAINT ck_funnel_stage_kind CHECK (kind IN ('in_progress','won','lost')), \n\tCONSTRAINT ck_funnel_stage_color CHECK (color ~ '^#[0-9A-F]{6}$'), \n\tFOREIGN KEY(funnel_id) REFERENCES funnels (id) ON DELETE CASCADE\n)\n\n",
    "\nCREATE TABLE crm_basket_items (\n\tid UUID NOT NULL, \n\tbasket_id UUID NOT NULL, \n\tposition INTEGER NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tkind VARCHAR(16) NOT NULL, \n\tcatalog_item_id UUID, \n\tsku VARCHAR(128), \n\tquantity NUMERIC(24, 6) NOT NULL, \n\tunit VARCHAR(32) NOT NULL, \n\tunit_price NUMERIC(24, 6) NOT NULL, \n\tline_total NUMERIC(40, 2) NOT NULL, \n\tcustom_fields JSON NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_crm_basket_position UNIQUE (basket_id, position) DEFERRABLE INITIALLY DEFERRED, \n\tCONSTRAINT ck_crm_basket_item CHECK (kind IN ('product','service') AND quantity>0 AND unit_price>=0 AND position>=0), \n\tFOREIGN KEY(basket_id) REFERENCES crm_baskets (id) ON DELETE CASCADE, \n\tFOREIGN KEY(catalog_item_id) REFERENCES catalog_item (id) ON DELETE SET NULL\n)\n\n",
    "\nCREATE TABLE crm_leads (\n\ttitle VARCHAR(255) NOT NULL, \n\tfunnel_id UUID NOT NULL, \n\tstage_id UUID NOT NULL, \n\tposition_revision INTEGER NOT NULL, \n\tfirst_name VARCHAR(255), \n\tlast_name VARCHAR(255), \n\tmiddle_name VARCHAR(255), \n\tcompany_name VARCHAR(255), \n\tcontact_id UUID, \n\tcompany_id UUID, \n\tconversion_result JSON, \n\tconversion_key VARCHAR(200), \n\tconversion_fingerprint VARCHAR(64), \n\tid UUID NOT NULL, \n\tcreated_by UUID NOT NULL, \n\tupdated_by UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_lead_stage FOREIGN KEY(funnel_id, stage_id) REFERENCES funnel_stages (funnel_id, id) DEFERRABLE INITIALLY DEFERRED, \n\tCONSTRAINT ck_lead_position_revision CHECK (position_revision>0), \n\tCONSTRAINT ck_lead_title CHECK (char_length(btrim(title)) BETWEEN 1 AND 255), \n\tFOREIGN KEY(contact_id) REFERENCES contacts (id) ON DELETE SET NULL, \n\tFOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE SET NULL\n)\n\n",
    "CREATE INDEX ix_lead_kanban ON crm_leads (funnel_id, stage_id, updated_at, id)",
    "\nCREATE TABLE crm_deals (\n\ttitle VARCHAR(255) NOT NULL, \n\tfunnel_id UUID NOT NULL, \n\tstage_id UUID NOT NULL, \n\tposition_revision INTEGER NOT NULL, \n\tsource_lead_id UUID, \n\tsource_lead_snapshot JSON, \n\tlifecycle_state VARCHAR(20) NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_by UUID NOT NULL, \n\tupdated_by UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_deal_stage FOREIGN KEY(funnel_id, stage_id) REFERENCES funnel_stages (funnel_id, id) DEFERRABLE INITIALLY DEFERRED, \n\tCONSTRAINT ck_deal_position_revision CHECK (position_revision>0), \n\tCONSTRAINT ck_deal_title CHECK (char_length(btrim(title)) BETWEEN 1 AND 255), \n\tFOREIGN KEY(source_lead_id) REFERENCES crm_leads (id) ON DELETE RESTRICT\n)\n\n",
    "CREATE INDEX ix_deal_kanban ON crm_deals (funnel_id, stage_id, updated_at, id)",
    "\nCREATE TABLE crm_deal_companies (\n\tdeal_id UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tPRIMARY KEY (deal_id, company_id), \n\tFOREIGN KEY(deal_id) REFERENCES crm_deals (id) ON DELETE CASCADE, \n\tFOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE RESTRICT\n)\n\n",
    "\nCREATE TABLE crm_deal_contacts (\n\tdeal_id UUID NOT NULL, \n\tcontact_id UUID NOT NULL, \n\tPRIMARY KEY (deal_id, contact_id), \n\tFOREIGN KEY(deal_id) REFERENCES crm_deals (id) ON DELETE CASCADE, \n\tFOREIGN KEY(contact_id) REFERENCES contacts (id) ON DELETE RESTRICT\n)\n\n",
    "\nCREATE TABLE crm_position_history (\n\tid UUID NOT NULL, \n\tmodel_key VARCHAR(32) NOT NULL, \n\trecord_id UUID NOT NULL, \n\tprevious JSON, \n\tcurrent JSON NOT NULL, \n\tprevious_revision INTEGER, \n\tcurrent_revision INTEGER NOT NULL, \n\treason VARCHAR(32) NOT NULL, \n\tactor_id UUID NOT NULL, \n\toccurred_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_position_history_model CHECK (model_key IN ('crm.lead','crm.deal')), \n\tCONSTRAINT ck_position_history_reason CHECK (reason IN ('created','manual_move','funnel_changed','stage_deleted')), \n\tCONSTRAINT ck_position_history_revision CHECK (current_revision > 0 AND (previous_revision IS NULL OR current_revision = previous_revision + 1)), \n\tCONSTRAINT uq_position_history_revision UNIQUE (model_key, record_id, current_revision)\n)\n\n",
    "CREATE INDEX ix_position_history_card_time ON crm_position_history (model_key, record_id, occurred_at)",
    "CREATE INDEX ix_position_history_time ON crm_position_history (occurred_at)",
    "CREATE UNIQUE INDEX uq_funnel_won_stage ON funnel_stages (funnel_id) WHERE kind = 'won'",
    "INSERT INTO funnels (id,model_key,name,is_default,revision,created_by,updated_by) VALUES ('63dfc77f-b9b3-552e-92cb-e4d75e96340b','crm.lead','Лиды',true,1,'00000000-0000-0000-0000-000000000000','00000000-0000-0000-0000-000000000000')",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position,kind) VALUES ('9748c7f8-dc6a-55b7-bf60-85c0f61e5486','63dfc77f-b9b3-552e-92cb-e4d75e96340b','Новый','#3B82F6',0,'in_progress')",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position,kind) VALUES ('5ee3f956-1126-5b71-b460-8d46aee2622a','63dfc77f-b9b3-552e-92cb-e4d75e96340b','В работе','#06B6D4',1,'in_progress')",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position,kind) VALUES ('ff28fe8e-5505-5c74-a56c-80ec12165ea3','63dfc77f-b9b3-552e-92cb-e4d75e96340b','Успешный','#84CC16',2,'won')",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position,kind) VALUES ('fb40fec7-4bb5-51aa-906a-7c8f4d2c9817','63dfc77f-b9b3-552e-92cb-e4d75e96340b','Неудачный','#EF4444',3,'lost')",
    "INSERT INTO funnels (id,model_key,name,is_default,revision,created_by,updated_by) VALUES ('96c1523e-6fbc-52e0-a140-9504c9a758ac','crm.deal','Сделки',true,1,'00000000-0000-0000-0000-000000000000','00000000-0000-0000-0000-000000000000')",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position,kind) VALUES ('c04321a5-1a5b-5d93-83c7-999894bae067','96c1523e-6fbc-52e0-a140-9504c9a758ac','Новый','#3B82F6',0,'in_progress')",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position,kind) VALUES ('249ddfdc-b968-58d2-863b-55ee3a78ab3d','96c1523e-6fbc-52e0-a140-9504c9a758ac','В работе','#06B6D4',1,'in_progress')",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position,kind) VALUES ('d22b4791-cfc8-552d-82eb-4e1c461b342a','96c1523e-6fbc-52e0-a140-9504c9a758ac','Успешный','#84CC16',2,'won')",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position,kind) VALUES ('6b7e9469-e6fa-5f8a-9690-1f11a7965e89','96c1523e-6fbc-52e0-a140-9504c9a758ac','Неудачный','#EF4444',3,'lost')",
)


def upgrade() -> None:
    """Создаёт новый срез и default-процессы в tenant search_path."""
    for statement in DDL:
        op.execute(statement)


def downgrade() -> None:
    """Удаляет только таблицы нового среза в обратном порядке зависимостей."""
    for name in (
        "crm_position_history",
        "crm_deal_contacts",
        "crm_deal_companies",
        "crm_deals",
        "crm_leads",
        "crm_basket_items",
        "funnel_stages",
        "funnels",
        "crm_baskets",
    ):
        op.execute("DROP TABLE " + name)
