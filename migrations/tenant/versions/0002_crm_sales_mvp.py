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
    "\nCREATE TABLE funnel_stages (\n\tid UUID NOT NULL, \n\tfunnel_id UUID NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\tcolor VARCHAR(16) NOT NULL, \n\tposition INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_funnel_stage_owner UNIQUE (funnel_id, id), \n\tCONSTRAINT uq_funnel_stage_position UNIQUE (funnel_id, position) DEFERRABLE INITIALLY DEFERRED, \n\tCONSTRAINT ck_funnel_stage_position CHECK (position>=0), \n\tFOREIGN KEY(funnel_id) REFERENCES funnels (id) ON DELETE CASCADE\n)\n\n",
    "\nCREATE TABLE crm_basket_items (\n\tid UUID NOT NULL, \n\tbasket_id UUID NOT NULL, \n\tposition INTEGER NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tkind VARCHAR(16) NOT NULL, \n\tcatalog_item_id UUID, \n\tsku VARCHAR(128), \n\tquantity NUMERIC(24, 6) NOT NULL, \n\tunit VARCHAR(32) NOT NULL, \n\tunit_price NUMERIC(24, 6) NOT NULL, \n\tline_total NUMERIC(40, 2) NOT NULL, \n\tcustom_fields JSON NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_crm_basket_position UNIQUE (basket_id, position) DEFERRABLE INITIALLY DEFERRED, \n\tCONSTRAINT ck_crm_basket_item CHECK (kind IN ('product','service') AND quantity>0 AND unit_price>=0 AND position>=0), \n\tFOREIGN KEY(basket_id) REFERENCES crm_baskets (id) ON DELETE CASCADE, \n\tFOREIGN KEY(catalog_item_id) REFERENCES catalog_item (id) ON DELETE SET NULL\n)\n\n",
    "\nCREATE TABLE crm_leads (\n\ttitle VARCHAR(255) NOT NULL, \n\tfunnel_id UUID NOT NULL, \n\tstage_id UUID NOT NULL, \n\tposition_revision INTEGER NOT NULL, \n\tfirst_name VARCHAR(255), \n\tlast_name VARCHAR(255), \n\tmiddle_name VARCHAR(255), \n\tcompany_name VARCHAR(255), \n\tcontact_id UUID, \n\tcompany_id UUID, \n\tconversion_result JSON, \n\tconversion_key VARCHAR(200), \n\tconversion_fingerprint VARCHAR(64), \n\tid UUID NOT NULL, \n\tcreated_by UUID NOT NULL, \n\tupdated_by UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_lead_stage FOREIGN KEY(funnel_id, stage_id) REFERENCES funnel_stages (funnel_id, id), \n\tCONSTRAINT ck_lead_position_revision CHECK (position_revision>0), \n\tCONSTRAINT ck_lead_title CHECK (char_length(btrim(title)) BETWEEN 1 AND 255), \n\tFOREIGN KEY(contact_id) REFERENCES contacts (id) ON DELETE SET NULL, \n\tFOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE SET NULL\n)\n\n",
    "CREATE INDEX ix_lead_kanban ON crm_leads (funnel_id, stage_id, updated_at, id)",
    "\nCREATE TABLE crm_deals (\n\ttitle VARCHAR(255) NOT NULL, \n\tfunnel_id UUID NOT NULL, \n\tstage_id UUID NOT NULL, \n\tposition_revision INTEGER NOT NULL, \n\tsource_lead_id UUID, \n\tsource_lead_snapshot JSON, \n\tlifecycle_state VARCHAR(20) NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_by UUID NOT NULL, \n\tupdated_by UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_deal_stage FOREIGN KEY(funnel_id, stage_id) REFERENCES funnel_stages (funnel_id, id), \n\tCONSTRAINT ck_deal_position_revision CHECK (position_revision>0), \n\tCONSTRAINT ck_deal_title CHECK (char_length(btrim(title)) BETWEEN 1 AND 255), \n\tFOREIGN KEY(source_lead_id) REFERENCES crm_leads (id) ON DELETE RESTRICT\n)\n\n",
    "CREATE INDEX ix_deal_kanban ON crm_deals (funnel_id, stage_id, updated_at, id)",
    "\nCREATE TABLE crm_deal_companies (\n\tdeal_id UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tPRIMARY KEY (deal_id, company_id), \n\tFOREIGN KEY(deal_id) REFERENCES crm_deals (id) ON DELETE CASCADE, \n\tFOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE RESTRICT\n)\n\n",
    "\nCREATE TABLE crm_deal_contacts (\n\tdeal_id UUID NOT NULL, \n\tcontact_id UUID NOT NULL, \n\tPRIMARY KEY (deal_id, contact_id), \n\tFOREIGN KEY(deal_id) REFERENCES crm_deals (id) ON DELETE CASCADE, \n\tFOREIGN KEY(contact_id) REFERENCES contacts (id) ON DELETE RESTRICT\n)\n\n",
    "INSERT INTO funnels (id,model_key,name,is_default,revision,created_by,updated_by) VALUES ('63dfc77f-b9b3-552e-92cb-e4d75e96340b','crm.lead','Лиды',true,1,'00000000-0000-0000-0000-000000000000','00000000-0000-0000-0000-000000000000')",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position) VALUES ('b0231287-49a1-5e52-bff4-754d952289fa','63dfc77f-b9b3-552e-92cb-e4d75e96340b','Новый','neutral',0)",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position) VALUES ('0cf2266a-0b63-5189-8f6f-fa402a3b7a6b','63dfc77f-b9b3-552e-92cb-e4d75e96340b','В работе','neutral',1)",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position) VALUES ('5811cc1d-7541-5bb0-89af-dff0dea16dbb','63dfc77f-b9b3-552e-92cb-e4d75e96340b','Квалифицирован','neutral',2)",
    "INSERT INTO funnels (id,model_key,name,is_default,revision,created_by,updated_by) VALUES ('96c1523e-6fbc-52e0-a140-9504c9a758ac','crm.deal','Сделки',true,1,'00000000-0000-0000-0000-000000000000','00000000-0000-0000-0000-000000000000')",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position) VALUES ('a878a3b9-f8d8-5cc5-97a1-e21877aef4cc','96c1523e-6fbc-52e0-a140-9504c9a758ac','Новая','neutral',0)",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position) VALUES ('fb912824-f5f8-5065-bbbe-c59071bc6028','96c1523e-6fbc-52e0-a140-9504c9a758ac','Согласование','neutral',1)",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position) VALUES ('1e69b648-9309-5b9d-9ff9-ae6b0206d053','96c1523e-6fbc-52e0-a140-9504c9a758ac','Подтверждена','neutral',2)",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position) VALUES ('dbe3e49e-56f1-5dfa-9a67-a0f892c5ebd4','96c1523e-6fbc-52e0-a140-9504c9a758ac','Исполнение','neutral',3)",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position) VALUES ('02a60165-f17f-5b2f-b963-a722e4d433a4','96c1523e-6fbc-52e0-a140-9504c9a758ac','Расчёты','neutral',4)",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position) VALUES ('09e1eb44-c2de-5577-9b3d-47d50984f6a7','96c1523e-6fbc-52e0-a140-9504c9a758ac','Завершена','neutral',5)",
    "INSERT INTO funnel_stages (id,funnel_id,name,color,position) VALUES ('08575c6a-a54c-5c3c-baf4-5240f3129583','96c1523e-6fbc-52e0-a140-9504c9a758ac','Отменена','neutral',6)",
)


def upgrade() -> None:
    """Создаёт новый срез и default-процессы в tenant search_path."""
    for statement in DDL:
        op.execute(statement)


def downgrade() -> None:
    """Удаляет только таблицы нового среза в обратном порядке зависимостей."""
    for name in (
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
