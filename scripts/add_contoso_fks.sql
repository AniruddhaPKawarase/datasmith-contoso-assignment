-- Contoso star-schema foreign keys. Not enforced during load (\COPY skips
-- constraint checks for speed); added here so introspection.py picks them
-- up + join_graph.py can find shared keys for cross-table composition.
--
-- Run: docker exec -i scm-postgres psql -U odoo -d contoso < scripts/add_contoso_fks.sql

BEGIN;

-- ─── Primary keys on dim tables (required before FK constraints) ────
ALTER TABLE dimdate                ADD PRIMARY KEY (datekey);
ALTER TABLE dimcustomer            ADD PRIMARY KEY (customerkey);
ALTER TABLE dimproduct             ADD PRIMARY KEY (productkey);
ALTER TABLE dimstore               ADD PRIMARY KEY (storekey);
ALTER TABLE dimpromotion           ADD PRIMARY KEY (promotionkey);
ALTER TABLE dimcurrency            ADD PRIMARY KEY (currencykey);
ALTER TABLE dimchannel             ADD PRIMARY KEY (channelkey);
ALTER TABLE dimproductcategory     ADD PRIMARY KEY (productcategorykey);
ALTER TABLE dimproductsubcategory  ADD PRIMARY KEY (productsubcategorykey);
ALTER TABLE dimsalesterritory      ADD PRIMARY KEY (salesterritorykey);
ALTER TABLE dimemployee            ADD PRIMARY KEY (employeekey);
ALTER TABLE dimgeography           ADD PRIMARY KEY (geographykey);

-- ─── FactOnlineSales ────────────────────────────────────────────────
ALTER TABLE factonlinesales ADD CONSTRAINT fk_fos_date       FOREIGN KEY (datekey)         REFERENCES dimdate(datekey) NOT VALID;
ALTER TABLE factonlinesales ADD CONSTRAINT fk_fos_customer   FOREIGN KEY (customerkey)     REFERENCES dimcustomer(customerkey) NOT VALID;
ALTER TABLE factonlinesales ADD CONSTRAINT fk_fos_product    FOREIGN KEY (productkey)      REFERENCES dimproduct(productkey) NOT VALID;
ALTER TABLE factonlinesales ADD CONSTRAINT fk_fos_store      FOREIGN KEY (storekey)        REFERENCES dimstore(storekey) NOT VALID;
ALTER TABLE factonlinesales ADD CONSTRAINT fk_fos_promotion  FOREIGN KEY (promotionkey)    REFERENCES dimpromotion(promotionkey) NOT VALID;
ALTER TABLE factonlinesales ADD CONSTRAINT fk_fos_currency   FOREIGN KEY (currencykey)     REFERENCES dimcurrency(currencykey) NOT VALID;

-- ─── FactSales ──────────────────────────────────────────────────────
ALTER TABLE factsales ADD CONSTRAINT fk_fs_date        FOREIGN KEY (datekey)         REFERENCES dimdate(datekey) NOT VALID;
ALTER TABLE factsales ADD CONSTRAINT fk_fs_channel     FOREIGN KEY (channelkey)      REFERENCES dimchannel(channelkey) NOT VALID;
ALTER TABLE factsales ADD CONSTRAINT fk_fs_store       FOREIGN KEY (storekey)        REFERENCES dimstore(storekey) NOT VALID;
ALTER TABLE factsales ADD CONSTRAINT fk_fs_product     FOREIGN KEY (productkey)      REFERENCES dimproduct(productkey) NOT VALID;
ALTER TABLE factsales ADD CONSTRAINT fk_fs_promotion   FOREIGN KEY (promotionkey)    REFERENCES dimpromotion(promotionkey) NOT VALID;
ALTER TABLE factsales ADD CONSTRAINT fk_fs_currency    FOREIGN KEY (currencykey)     REFERENCES dimcurrency(currencykey) NOT VALID;

-- ─── FactSalesQuota ─────────────────────────────────────────────────
ALTER TABLE factsalesquota ADD CONSTRAINT fk_fsq_channel    FOREIGN KEY (channelkey)      REFERENCES dimchannel(channelkey) NOT VALID;
ALTER TABLE factsalesquota ADD CONSTRAINT fk_fsq_store      FOREIGN KEY (storekey)        REFERENCES dimstore(storekey) NOT VALID;
ALTER TABLE factsalesquota ADD CONSTRAINT fk_fsq_product    FOREIGN KEY (productkey)      REFERENCES dimproduct(productkey) NOT VALID;
ALTER TABLE factsalesquota ADD CONSTRAINT fk_fsq_currency   FOREIGN KEY (currencykey)     REFERENCES dimcurrency(currencykey) NOT VALID;
ALTER TABLE factsalesquota ADD CONSTRAINT fk_fsq_date       FOREIGN KEY (datekey)         REFERENCES dimdate(datekey) NOT VALID;

-- ─── Dim hierarchy ──────────────────────────────────────────────────
ALTER TABLE dimproduct            ADD CONSTRAINT fk_dp_subcategory  FOREIGN KEY (productsubcategorykey) REFERENCES dimproductsubcategory(productsubcategorykey) NOT VALID;
ALTER TABLE dimproductsubcategory ADD CONSTRAINT fk_dps_category    FOREIGN KEY (productcategorykey)    REFERENCES dimproductcategory(productcategorykey) NOT VALID;
-- Territory bridge (snowflake via geography). Store/Customer link to
-- DimSalesTerritory via geographykey; DimSalesTerritory.employeekey is
-- the sales-rep who owns the territory.
ALTER TABLE dimcustomer        ADD CONSTRAINT fk_dc_geography    FOREIGN KEY (geographykey)          REFERENCES dimgeography(geographykey) NOT VALID;
ALTER TABLE dimstore           ADD CONSTRAINT fk_ds_geography    FOREIGN KEY (geographykey)          REFERENCES dimgeography(geographykey) NOT VALID;
ALTER TABLE dimsalesterritory  ADD CONSTRAINT fk_dst_geography   FOREIGN KEY (geographykey)          REFERENCES dimgeography(geographykey) NOT VALID;
ALTER TABLE dimsalesterritory  ADD CONSTRAINT fk_dst_employee    FOREIGN KEY (employeekey)           REFERENCES dimemployee(employeekey) NOT VALID;

COMMIT;
