-- ============================================================
-- Metadata 字段索引创建脚本
-- 用于为 SeekDB 集合的 metadata JSON 字段创建索引
--
-- 注意：OceanBase/SeekDB 需要使用生成列（GENERATED COLUMN）方式创建索引
-- 先创建生成列，然后在生成列上创建索引
-- ============================================================

-- 使用说明：
-- 1. 替换 <collection_name> 为实际的集合名称
-- 2. 集合对应的表名格式为：c$v1$<collection_name>
-- 3. 执行前请确保集合已创建并包含数据
-- 4. 如果生成列已存在，ALTER TABLE 语句会失败，可以忽略错误继续执行

-- ============================================================
-- 示例：为 "book_info" 集合创建 metadata 索引
-- ============================================================

-- 表名（根据集合名称调整）
-- SET @table_name = 'c$v1$book_info';

-- ============================================================
-- 1. 为 genre 字段创建生成列和索引
-- ============================================================
-- 创建生成列
ALTER TABLE c$v1$book_info
ADD COLUMN gen_genre VARCHAR(100)
GENERATED ALWAYS AS (metadata->'$.genre');

-- 创建索引
CREATE INDEX idx_metadata_genre ON c$v1$book_info(gen_genre);

-- ============================================================
-- 2. 为 author 字段创建生成列和索引
-- ============================================================
-- 创建生成列
ALTER TABLE c$v1$book_info
ADD COLUMN gen_author VARCHAR(200)
GENERATED ALWAYS AS (metadata->'$.author');

-- 创建索引
CREATE INDEX idx_metadata_author ON c$v1$book_info(gen_author);

-- ============================================================
-- 3. 为 year 字段创建生成列和索引
-- ============================================================
-- 创建生成列
ALTER TABLE c$v1$book_info
ADD COLUMN gen_year INT
GENERATED ALWAYS AS (metadata->>'$.year');

-- 创建索引
CREATE INDEX idx_metadata_year ON c$v1$book_info(gen_year);

-- ============================================================
-- 4. 为 user_rating 字段创建生成列和索引
-- ============================================================
-- 创建生成列
ALTER TABLE c$v1$book_info
ADD COLUMN gen_user_rating FLOAT
GENERATED ALWAYS AS (metadata->>'$.user_rating');

-- 创建索引
CREATE INDEX idx_metadata_user_rating ON c$v1$book_info(gen_user_rating);

-- ============================================================
-- 5. 为 reviews 字段创建生成列和索引（可选）
-- ============================================================
-- 创建生成列
ALTER TABLE c$v1$book_info
ADD COLUMN gen_reviews INT
GENERATED ALWAYS AS (metadata->>'$.reviews');

-- 创建索引
CREATE INDEX idx_metadata_reviews ON c$v1$book_info(gen_reviews);

-- ============================================================
-- 6. 为 price 字段创建生成列和索引（可选）
-- ============================================================
-- 创建生成列
ALTER TABLE c$v1$book_info
ADD COLUMN gen_price FLOAT
GENERATED ALWAYS AS (metadata->>'$.price');

-- 创建索引
CREATE INDEX idx_metadata_price ON c$v1$book_info(gen_price);

-- ============================================================
-- 7. 为 name 字段创建生成列和索引（可选，用于书名搜索）
-- ============================================================
-- 创建生成列
ALTER TABLE c$v1$book_info
ADD COLUMN gen_name VARCHAR(500)
GENERATED ALWAYS AS (metadata->'$.name');

-- 创建索引
CREATE INDEX idx_metadata_name ON c$v1$book_info(gen_name);

-- ============================================================
-- 查看已创建的索引
-- ============================================================
-- SHOW INDEX FROM c$v1$book_info;

-- ============================================================
-- 删除索引和生成列（如果需要重建）
-- ============================================================
-- 注意：删除生成列前需要先删除索引
-- DROP INDEX IF EXISTS idx_metadata_genre ON c$v1$book_info;
-- ALTER TABLE c$v1$book_info DROP COLUMN gen_genre;
--
-- DROP INDEX IF EXISTS idx_metadata_author ON c$v1$book_info;
-- ALTER TABLE c$v1$book_info DROP COLUMN gen_author;
--
-- DROP INDEX IF EXISTS idx_metadata_year ON c$v1$book_info;
-- ALTER TABLE c$v1$book_info DROP COLUMN gen_year;
--
-- DROP INDEX IF EXISTS idx_metadata_user_rating ON c$v1$book_info;
-- ALTER TABLE c$v1$book_info DROP COLUMN gen_user_rating;
--
-- DROP INDEX IF EXISTS idx_metadata_reviews ON c$v1$book_info;
-- ALTER TABLE c$v1$book_info DROP COLUMN gen_reviews;
--
-- DROP INDEX IF EXISTS idx_metadata_price ON c$v1$book_info;
-- ALTER TABLE c$v1$book_info DROP COLUMN gen_price;
--
-- DROP INDEX IF EXISTS idx_metadata_name ON c$v1$book_info;
-- ALTER TABLE c$v1$book_info DROP COLUMN gen_name;

