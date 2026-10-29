# مقارنة قواعد بيانات المتجهات — أكتوبر 2026

**تاريخ الإعداد:** 2026-10-29
**النطاق:** pgvector · Qdrant · Milvus (وZilliz Cloud) · Weaviate · Pinecone · Chroma
**السؤال:** أيّها الأنسب لفريق من ٥ مطوّرين، عنده نحو ١٠ مليون متجه لنصوص عربية وإنجليزية، وميزانية تشغيل أقل من ٥٠٠ دولار في الشهر، ويستخدم PostgreSQL أصلًا؟

---

## الخلاصة

**الاختيار: pgvector داخل PostgreSQL** (فهرس HNSW على `halfvec`، مع iterative scans للبحث المفلتر).
**البديل الثاني: Qdrant** مُستضاف ذاتيًّا أو على Qdrant Cloud.
**ننتقل** حين يثبت القياس أن Postgres صار هو عنق الزجاجة (التفاصيل في القسم ٤). حجم البيانات وحده لا يكفي سببًا.

السبب باختصار: ١٠ مليون متجه حجم متوسط، يدخل في ذاكرة خادم Postgres واحد معقول لو خزّنّا المتجهات بنصف الدقة. وكون الفريق يعرف Postgres أصلًا يوفّر عليه نظامًا ثانيًا يشغّله ويراقبه ويعمل له نسخًا احتياطية، ويوفّر مزامنة البيانات بين نظامين. في فريق من ٥ أشخاص، هذا التوفير أثمن من فرق الأداء الذي تظهره البنشماركات.

---

## ١. جدول المقارنة

| | **pgvector** | **Qdrant** | **Milvus / Zilliz** | **Weaviate** | **Pinecone** | **Chroma** |
|---|---|---|---|---|---|---|
| آخر إصدار (تحقّقت منه) | 0.8.7 (2026-10-05) | v1.20.0 (2026-10-22) | v3.0.4 (2026-10-26) | v1.40.3 (2026-10-28) | خدمة مغلقة | 1.5.9 (2026-05-05) |
| الترخيص | PostgreSQL License (مفتوح) | Apache-2.0 | Apache-2.0 | BSD-3 للنواة، وميزات مجلّد `wl/` تجارية بمفتاح ترخيص | مغلق المصدر | Apache-2.0 |
| تشغيل ذاتي | نعم (امتداد لـ Postgres) | نعم | نعم (Standalone أو Distributed) | نعم | لا | نعم (عقدة واحدة) |
| نسخة مُدارة | أي Postgres مُدار (RDS، Aurora، Azure، Supabase…) | Qdrant Cloud | Zilliz Cloud | Weaviate Cloud | Pinecone فقط | Chroma Cloud |
| أقل سعر مدفوع للنسخة المُدارة | سعر خادم Postgres | بحسب الاستهلاك (لا أسعار منشورة) | Serverless من $0، و Dedicated Enterprise من $197/شهر | Flex بحدّ أدنى $45/شهر | Standard بحدّ أدنى $50/شهر | Starter بـ $0 + استهلاك، و Team بـ $250/شهر |

---

## ٢. كل قاعدة بالتفصيل

### pgvector

- **الترخيص:** ملف LICENSE في المستودع هو نصّ رخصة PostgreSQL ([LICENSE](https://github.com/pgvector/pgvector/blob/master/LICENSE)). pgvectorscale من Tiger Data مرخّص بالرخصة نفسها ([GitHub](https://github.com/timescale/pgvectorscale)).
- **التشغيل:** امتداد يُضاف إلى Postgres الموجود. متاح على Amazon RDS، وأعلنت AWS دعم 0.8.0 في نوفمبر 2024 ([AWS](https://aws.amazon.com/about-aws/whats-new/2024/11/amazon-rds-for-postgresql-pgvector-080/)). **pgvectorscale غير متاح على RDS**، لأنه مكتوب بـ Rust ولا يمكن تحميله عبر pg_tle ([طلب ميزة على re:Post](https://repost.aws/questions/QUEgTTEzDeQdCoo5UJIEGAYw/add-pgvectorscale-extension-to-amazon-rds-aurora-postgresql-for-diskann-hnsw-hybrid-vector-search)). من يريده يحتاج Postgres يديره بنفسه.
- **الإمكانات** ([README](https://github.com/pgvector/pgvector)):
  - فهرسا HNSW و IVFFlat.
  - حدود أبعاد الفهرس: `vector` حتى 2,000 بُعد، و`halfvec` حتى 4,000، و`bit` حتى 64,000.
  - تكميم ثنائي عن طريق expression index، ثم إعادة ترتيب النتائج بالمتجهات الأصلية.
  - iterative index scans منذ 0.8.0.
- **السعر المُدار:** لا تسعير خاص بالمتجهات، فأنت تدفع ثمن خادم Postgres. مثال: `db.r7g.xlarge` (4 vCPU و32 GiB) على RDS PostgreSQL في us-east-1 يكلّف $0.478 في الساعة، أي نحو $349 في الشهر on-demand، أو نحو $255 بحجز سنة ([Bytebase](https://www.bytebase.com/dbcost/rds/instance/db.r7g.xlarge/)، [Vantage](https://instances.vantage.sh/aws/rds/db.r7g.xlarge)). التخزين والـ IOPS تُحسب منفصلة.
- **البنشمارك المنشور:**
  - Tiger Data (صاحبة pgvectorscale، أي مصدر منحاز) قاست 50 مليون متجه Cohere بـ 768 بُعدًا على r6id.4xlarge.
  - النتيجة عند recall 99%: Postgres مع pgvectorscale حقّق **471.6 QPS** مقابل **41.5 QPS** لـ Qdrant 1.13.4. لكن زمن p99 كان 74.6ms لـ Postgres مقابل 38.7ms لـ Qdrant.
  - بناء الفهرس استغرق نحو 11.1 ساعة لـ Postgres مقابل 3.3 ساعة لـ Qdrant ([Tiger Data, 2025](https://www.tigerdata.com/blog/pgvector-vs-qdrant)).
  - تحفّظات: النسخ المستخدمة قديمة (pgvector 0.6.1 و pgvectorscale 0.7.0)، والاختبار بلا فلترة، والكاتب نفسه يقرّ بأن ضبط Qdrant ربما لم يكن الأمثل.
  - pgvector مدرج أيضًا في [ANN-Benchmarks](https://ann-benchmarks.com/) و[VectorDBBench](https://github.com/zilliztech/VectorDBBench).
- **الحدود المعروفة:**
  - **الفلترة تحدث بعد مسح الفهرس.** إذا طابق الشرط 10% من الصفوف، يرجع HNSW بالإعداد الافتراضي `ef_search=40` نحو 4 نتائج في المتوسط. الحلول: iterative scans، أو partial indexes، أو التقسيم (partitioning) ([README](https://github.com/pgvector/pgvector)).
  - **بناء الفهرس سريع فقط حين يتسع له `maintenance_work_mem`.** بناء فهرس لـ 10 ملايين متجه يحتاج ذاكرة كبيرة وقتًا معتبرًا.
  - **الثغرات الأمنية:** النسخة 0.8.7 أصلحت buffer overflow في بناء فهارس IVFFlat يسمح بتنفيذ كود (CVE-2026-103484) ([postgresql.org](https://www.postgresql.org/about/news/pgvector-087-released-3392/)). لذلك يلزم تتبّع النسخ.
  - **التوسّع الأفقي غير مدمج.** عند حجم أكبر بكثير يصبح الحل sharding يدويًّا أو Citus.
  - **البحث النصي بالعربي:** Postgres يأتي بـ `arabic_stem` من Snowball ([الوثائق](https://www.postgresql.org/docs/current/textsearch-dictionaries.html)). لكن هناك أمثلة على أنه يجذّر الكلمات بشكل رديء، مثل «فجوات» التي تصير «جوا»، والحل المقترح قاموس Hunspell ([Misraj](https://misraj.sa/en/blog/full-text-search-in-postgres)). هذا يهمّ إذا اعتمدنا البحث الهجين.

### Qdrant

- **الترخيص:** Apache-2.0 ([GitHub](https://github.com/qdrant/qdrant)). آخر إصدار v1.20.0 بتاريخ 2026-10-22.
- **التشغيل:** ذاتي (Docker أو Kubernetes)، أو Qdrant Cloud (مُدار)، أو Hybrid Cloud، أو Private Cloud.
- **السعر المُدار** ([qdrant.tech/pricing](https://qdrant.tech/pricing/)):
  - Free: مجاني دائمًا، بمواصفات 0.5 vCPU و1GB RAM و4GB قرص، على عقدة واحدة.
  - Standard: بحسب الاستهلاك. الفوترة ساعية على vCPU والذاكرة والتخزين والنسخ الاحتياطية، مع SLA بنسبة 99.5%.
  - Premium: بحدّ أدنى للإنفاق، مع SSO و SLA بنسبة 99.9%.
  - **الصفحة الرسمية لا تنشر أسعار الوحدات.** الأرقام المتداولة في المواقع الأخرى (من $25 إلى $50 شهريًّا) تتضارب فيما بينها، فاستخدم الحاسبة الرسمية.
- **البنشمارك المنشور:**
  - [بنشمارك Qdrant](https://qdrant.tech/benchmarks/) يقارنها بـ Milvus و Weaviate و Elasticsearch و Redis على مجموعات مثل dbpedia-openai-1M و deep-image-96 (10 ملايين متجه).
  - الخلاصة المعلنة: Qdrant الأعلى في RPS والأقل في زمن الاستجابة في أغلب السيناريوهات، و Milvus الأسرع في بناء الفهرس.
  - تحفّظات: الجهة منحازة باعترافها، وآخر تحديث للبيانات يونيو 2024، وبنشمارك الفلترة من فبراير 2023.
  - في [VectorDBBench](https://zilliz.com/benchmark) (ترعاه Zilliz)، على 1M × 768: QdrantCloud-16c64g حقّق 1,242 QPS بزمن p99 قدره 6.4ms و recall 0.947. وعلى 10M: 447 QPS ثابتًا، وبقي عند نحو 348 QPS مع إدخال 1000 صف في الثانية.
  - وفي بنشمارك Tiger Data المذكور أعلاه، كان لـ Qdrant أفضل زمن ذيلي (tail latency) وأسرع بناء فهرس، وأقل throughput عند recall 99%.
- **الحدود المعروفة:**
  - نظام منفصل عن Postgres، يحتاج مزامنة ونسخًا احتياطية ومراقبة خاصة به.
  - لا SQL ولا joins مع الجداول.
  - أسعار السحابة غير منشورة، فيصعب التقدير المسبق.
  - المتجهات الكاملة في الذاكرة مكلفة، وتحتاج تكميمًا (quantization) أو تخزينًا على القرص حتى تنزل التكلفة. هذا عامّ في محرّكات HNSW وليس خاصًّا بـ Qdrant.

### Milvus / Zilliz Cloud

- **الترخيص:** Apache-2.0 ([GitHub](https://github.com/milvus-io/milvus))، ومشروع تابع لـ LF AI & Data. آخر إصدار v3.0.4 بتاريخ 2026-10-26.
- **الجديد في 2026:** وصل Milvus 3.0 إلى GA في يوليو 2026 بتصميم «lake-native» ([LF AI](https://lfaidata.foundation/blog/2026/07/29/milvus-3-0-is-here-lf-ai-datas-open-source-vector-database-goes-lake-native/)، [ملاحظات الإصدار](https://github.com/milvus-io/milvus-docs/blob/v3.0.x/site/en/release_notes.md)). أهم ما فيه:
  - External Collections فوق Iceberg و Parquet و Lance.
  - محرّك تخزين جديد اسمه Loon (Storage V3).
  - Snapshots.
  - تعديل المخطط (schema) أثناء التشغيل.
  - الميزات الجديدة اختيارية (opt-in)، ولا تراجع عنها بعد تفعيل صيغة تخزين جديدة.
- **التشغيل:** ذاتي (Standalone أو Distributed على Kubernetes)، أو مُدار عبر Zilliz Cloud.
- **السعر المُدار** ([zilliz.com/pricing](https://zilliz.com/pricing)):
  - Free: يشمل 5GB و2.5M vCU شهريًّا.
  - Serverless: يبدأ من $0.
  - Dedicated: السعر لكل مليون متجه بـ 768 بُعدًا في الشهر. Performance-optimized من $63، و Capacity-optimized من $16، و Tiered-storage من $5.
  - Enterprise: من $197 شهريًّا.
- **البنشمارك المنشور:**
  - VectorDBBench على 1M × 768 بميزانية $1,000 شهريًّا: ZillizCloud-8cu-perf حقّق 13,316 QPS بزمن p99 قدره 2ms و recall 0.938، و Milvus-16c64g-sq8 حقّق 5,973 QPS.
  - وعلى 10M × 768: Zilliz حقّق 7,385 QPS ثابتًا ونحو 1,860 QPS مع إدخال 1000 صف في الثانية. أما Milvus المُستضاف ذاتيًّا فهبط من 2,747 إلى 156 QPS تحت الإدخال نفسه ([zilliz.com/benchmark](https://zilliz.com/benchmark)).
  - **تحفّظ مهمّ:** الأداة من Zilliz نفسها ([المستودع يصرّح بذلك](https://github.com/zilliztech/VectorDBBench))، ولا تذكر الصفحة تاريخ الاختبار ولا النسخ. وقارن recall القيم: Milvus عند نحو 0.92 مقابل Qdrant عند نحو 0.95.
- **الحدود المعروفة:**
  - النسخة الموزّعة لها عدة مكوّنات (Proxy، Streaming Node، Woodpecker، عُقد query و data، وتخزين كائنات). هذا ثقيل على فريق من ٥ أشخاص بلا مسؤول بنية تحتية.
  - الأداء تحت الكتابة المستمرّة يهبط كثيرًا في النسخة المُستضافة ذاتيًّا، بحسب أرقام البنشمارك أعلاه.
  - عند الإطلاق، دعم Milvus 3.0 كان في SDKs بايثون و Go و Node.js، مع Java لاحقًا.

### Weaviate

- **الترخيص:** **تغيّر في سبتمبر 2026.** النواة ما زالت BSD-3-Clause، لكن الكود داخل مجلّد `wl/` صار تحت ترخيص Weaviate تجاري، ويُفعَّل بمفتاح ترخيص. هذا المجلّد يضم حاليًّا `backupdedupe` و `dbusers` و `namespaces` و `selfrecovery` ([LICENSE](https://github.com/weaviate/weaviate/blob/main/LICENSE)). آخر تعديل لنص الترخيص كان 2026-09-30. آخر إصدار v1.40.3 بتاريخ 2026-10-28.
- **التشغيل:** ذاتي، أو Weaviate Cloud (مشترك أو مخصّص).
- **السعر المُدار** ([weaviate.io/pricing](https://weaviate.io/pricing)):
  - Free: يشمل 100 ألف كائن و1GB ذاكرة.
  - **Flex:** حدّ أدنى $45 شهريًّا. الأبعاد من $0.00465 لكل مليون بُعد، والتخزين من $0.12 لكل GiB، والنسخ الاحتياطي من $0.03036 لكل GiB.
  - Premium: من نحو $400 شهريًّا.
  - السعر الفعلي لكل بُعد يتغيّر بحسب نوع الفهرس والضغط والمنطقة. وبعد تحوّل الخطط المدفوعة إلى HA افتراضيًّا، يُضرب استهلاك الأبعاد في عامل التكرار ([Weaviate blog](https://weaviate.io/blog/weaviate-cloud-pricing-update)).
- **البنشمارك المنشور:** يظهر Weaviate في [بنشمارك Qdrant](https://qdrant.tech/benchmarks/)، حيث يقول Qdrant إنه «الأقل تحسّنًا منذ الجولة السابقة»، وهذا مصدر منافس. ويظهر Weaviate Cloud ضمن [VectorDBBench](https://github.com/zilliztech/VectorDBBench). لم أجد رقمًا مستقلًّا حديثًا يصلح للمقارنة، فلا أنقل أرقامًا هنا.
- **الحدود المعروفة:**
  - بعض ميزات الإدارة صار خلف مفتاح ترخيص تجاري.
  - التسعير بالأبعاد مضروبًا في التكرار يصعب تقديره قبل التجربة.
  - نظام منفصل عن Postgres.

### Pinecone

- **الترخيص:** خدمة مغلقة المصدر، ولا تشغيل ذاتي.
- **السعر** ([pinecone.io/pricing](https://www.pinecone.io/pricing/)):

  | الخطة | الحدّ الأدنى الشهري | التخزين | Write Units | Read Units |
  |---|---|---|---|---|
  | Starter | مجاني | حتى 2GB | حتى 2M شهريًّا | حتى 1M شهريًّا |
  | Builder | $20 ثابتة | حتى 10GB | حتى 5M شهريًّا | حتى 2M شهريًّا |
  | Standard | $50 | $0.33 لكل GB شهريًّا | $4 إلى $4.50 لكل مليون | $16 إلى $18 لكل مليون |
  | Enterprise | $500 | $0.33 لكل GB شهريًّا | $6 إلى $6.75 لكل مليون | $24 إلى $27 لكل مليون |

- **قاعدة الفوترة المهمّة** ([docs](https://docs.pinecone.io/guides/manage-cost/understanding-cost)):
  - **الاستعلام يستهلك 1 RU لكل 1GB من حجم الـ namespace**، بحدّ أدنى 0.25 RU.
  - الكتابة تستهلك 1 WU لكل 1KB، بحدّ أدنى 5 WU للطلب.
- **البنشمارك المنشور:** في VectorDBBench على 1M × 768، حقّق Pinecone-p2.x8 نحو 1,147 QPS بزمن p99 قدره 13.7ms. وعلى 10M، حقّق 1,131 QPS ثابتًا ونحو 370 QPS تحت الإدخال ([zilliz.com/benchmark](https://zilliz.com/benchmark)). لكن p2 من نوع pods، وليس serverless الذي تقوم عليه الأسعار أعلاه.
- **الحدود المعروفة:**
  - ارتباط كامل بمزوّد واحد (vendor lock-in)، ولا تشغيل محلي في الإنتاج.
  - تكلفة القراءة تكبر مع حجم الـ namespace (التقدير في القسم ٣).
  - البيانات تخرج من بنيتك التحتية.

### Chroma

- **الترخيص:** Apache-2.0 ([GitHub](https://github.com/chroma-core/chroma)). آخر إصدار في GitHub هو 1.5.9 بتاريخ 2026-05-05.
- **التشغيل:** مضمّن داخل بايثون، أو خادم بعقدة واحدة، أو Chroma Cloud.
- **السعر المُدار** ([trychroma.com/pricing](https://www.trychroma.com/pricing)):
  - Starter: $0 مع $5 رصيدًا مجانيًّا.
  - Team: $250 شهريًّا تشمل $100 رصيدًا، مع SOC II.
  - Enterprise: سعر مخصّص.
  - الاستهلاك: الكتابة $2.50 لكل GiB، والتخزين $0.33 لكل GiB شهريًّا، والاستعلام $0.0075 لكل TiB مُستعلَم عنه، والشبكة $0.09 لكل GiB مُعاد.
- **البنشمارك المنشور:** لا يظهر Chroma في [ANN-Benchmarks](https://ann-benchmarks.com/) ولا في نتائج VectorDBBench القياسية، مع أنه مدعوم كعميل في الأداة. لم أجد رقمًا موثوقًا.
- **الحدود المعروفة:**
  - النسخة المفتوحة تعمل بعقدة واحدة وتتوسّع رأسيًّا فقط. الدليل الرسمي يحيل التوسّع الأفقي إلى النسخة الموزّعة أو Chroma Cloud ([Chroma Cookbook](https://cookbook.chromadb.dev/core/system_constraints/)).
  - لا replication ولا failover مدمجين.
  - المصادر الأخرى تضع سقفًا عمليًّا للتشغيل الذاتي بين 5 و10 ملايين متجه، وهذا بالضبط حجمنا ([Groovy Web](https://www.groovyweb.co/blog/vector-database-comparison-2026)).

---

## ٣. تقدير التكلفة لحالتنا (١٠ مليون متجه)

**الافتراضات:**
- نموذج تضمين متعدد اللغات يدعم العربي بـ **1024 بُعدًا**، وهو المعتاد في هذه الفئة.
- نحو 500 بايت من البيانات الوصفية (metadata) لكل سجل.
- عدد الاستعلامات 100 ألف أو 500 ألف شهريًّا.

**أحجام البيانات الخام:**
- بدقة float32: 10M × 1024 × 4 بايت ≈ **41GB**.
- بنصف الدقة (`halfvec`): نحو **20.5GB**.
- بالتكميم الثنائي (`bit`): نحو **1.3GB**.

| الخيار | الطريقة | التكلفة الشهرية التقديرية |
|---|---|---|
| **pgvector على Postgres الحالي** | إن كان الخادم الحالي فيه ذاكرة فائضة تكفي فهرس `halfvec` (أكثر من 20GB للمتجهات، والفهرس تقريبًا بالحجم نفسه، وهذا تقدير) | **≈ $0 إضافي**، والخطر هو التنافس على الذاكرة مع الشغل الأساسي |
| **pgvector على خادم Postgres مخصّص** | مثل RDS `db.r7g.xlarge` بـ 32GiB، مع `halfvec` أو فهرس ثنائي وإعادة ترتيب | **≈ $255 إلى $349** + التخزين (أقل من 500) |
| Pinecone Standard | التخزين نحو 46GB × $0.33 ≈ $15. كل استعلام ≈ 46 RU لأن الـ namespace بحجم 46GB. 100 ألف استعلام ≈ 4.6M RU ≈ $74. 500 ألف ≈ $368. الكتابة الأولى مرّة واحدة ≈ 46M WU ≈ $184 | **≈ $90 إلى $385**، وتتضاعف مع عدد الاستعلامات، وتقلّ لو قسّمنا الـ namespaces |
| Weaviate Flex | 10,240 مليون بُعد × $0.00465 ≈ $48 بأقل سعر، والسعر يرتفع بلا ضغط ومع عامل التكرار | **≈ $50 إلى $300**، ولا يُعرف الرقم إلا من الكونسول |
| Zilliz Dedicated | (1024/768) × 10M × سعر الفئة: tiered ≈ $67، و capacity ≈ $213، و performance ≈ $840 | **≈ $67 إلى $213** في الفئات الاقتصادية |
| Chroma Cloud Starter | التخزين نحو 45GiB × $0.33 ≈ $15. الاستعلام يمسح نحو 0.044TiB، أي ≈ $0.00033 للاستعلام، فيصير 100 ألف ≈ $33 و500 ألف ≈ $165. الكتابة الأولى ≈ $113 | **≈ $50 إلى $180**، ويضاف $250 لو احتجنا Team أو SOC II |
| Qdrant Cloud | لا أسعار منشورة | من الحاسبة الرسمية |

> هذه تقديرات من الأسعار المنشورة، وليست عروض أسعار. وتفسير «TiB queried» في Chroma افترضته = حجم المجموعة لكل استعلام، ولم أتحقّق منه في الوثائق.

---

## ٤. التوصية

### الاختيار: pgvector

1. **يكفي الحجم.** 10M × 1024 بنصف الدقة يساوي نحو 20GB للمتجهات. هذا يتسع في خادم بـ 32 إلى 64GB. ولو ضاقت الذاكرة، يُبنى فهرس ثنائي (`bit`، نحو 1.3GB) وتُعاد ترتيب النتائج بالـ `halfvec`، كما يوصي README.
2. **التكلفة.** صفر إضافي على الخادم الحالي، أو ≈ $255 إلى $349 لخادم RDS مخصّص. الاثنان أقل من $500، ولا تكلفة لكل استعلام تكبر مع الاستخدام.
3. **التشغيل.** لا نظام جديد يحتاج نسخًا احتياطية ومراقبة وصلاحيات وتدريبًا. المتجه في الصف نفسه مع النص والبيانات الوصفية، فلا مشكلة مزامنة. والفلترة بالـ SQL والصلاحيات (RLS) والـ transactions كلها متاحة مباشرة.
4. **العربي والإنجليزي.** جودة الاسترجاع متعدد اللغات تأتي من **نموذج التضمين** وليس من قاعدة البيانات. وأي قاعدة من الست تخزّن المتجه بالطريقة نفسها. القاعدة تفرق فقط في البحث الهجين، وهنا يحتاج Postgres عناية: `arabic_stem` ضعيف، فالأفضل قاموس Hunspell أو `pg_trgm` للنص العربي.

**إعدادات البداية المقترحة:**
- `halfvec(1024)` مع `hnsw (embedding halfvec_cosine_ops)`.
- `SET hnsw.iterative_scan = relaxed_order` للاستعلامات المفلترة.
- partial index أو partitioning لو كان هناك فلتر ثابت شائع، مثل اللغة أو الجهة.
- `maintenance_work_mem` كافٍ أثناء بناء الفهرس، والبناء في وقت هادئ.
- الترقية إلى pgvector 0.8.7 على الأقل بسبب CVE-2026-103484.
- قياس recall@10 و p95 على عيّنة حقيقية من الاستعلامات العربية والإنجليزية قبل الاعتماد.

**على RDS:** pgvectorscale و StreamingDiskANN غير متاحين. لو احتجناهما، يلزم Postgres مُدار ذاتيًّا على EC2 أو ما يشبهه.

### البديل الثاني: Qdrant

- **لماذا هو:** ترخيص Apache-2.0 بلا ميزات مقفولة، بخلاف Weaviate الآن. فيه تكميم ومتجهات على القرص. وأعطى أفضل زمن ذيلي وأسرع بناء فهرس في بنشمارك Tiger Data المنحاز ضده، وأداء ثابتًا تحت الكتابة في VectorDBBench الذي ترعاه جهة منافسة.
- **يعمل بطريقتين:** خادم واحد يديره الفريق، أو Qdrant Cloud بدفع الموارد بدل الدفع لكل استعلام.
- **لماذا لم أختر غيره:**
  - Milvus ثقيل تشغيليًّا لفريق بهذا الحجم.
  - Pinecone يربطنا بمزوّد واحد، وتكلفة القراءة تكبر مع حجم الـ namespace.
  - Chroma عند سقفه العملي في حجمنا.
  - Weaviate صار بعض ميزاته تجاريًّا منذ سبتمبر 2026.

### متى ننتقل من pgvector

ننتقل إلى Qdrant لو تحقّق **واحد أو أكثر** من هذه بعد القياس:

1. **الذاكرة:** الفهرس لم يعد يتسع في الذاكرة بعد `halfvec` والتكميم الثنائي، ويحدث هذا تقريبًا بعد 50 إلى 100 مليون متجه. أو صار الفهرس ينافس الشغل الأساسي على الذاكرة نفسها.
2. **الفلترة:** p95 للاستعلامات المفلترة يتجاوز الهدف المحدّد (مثلًا 100ms)، رغم iterative scans و partial indexes.
3. **الكتابة المستمرّة:** إدخال وتحديث متواصل بمعدّل عالٍ يسبّب ضغط vacuum أو بطء في الاستعلامات العادية.
4. **التوسّع الأفقي:** حاجة إلى توزيع على عدة عُقد أو multi-tenancy كبير.
5. **وقت إعادة البناء:** إعادة بناء الفهرس صارت تأخذ أطول مما يتحمّله وقت الصيانة.

**وقبل الانتقال:** جرّب أولًا pgvectorscale على Postgres مُدار ذاتيًّا، وجرّب read replica مخصّصة للبحث. الاثنان يحلّان كثيرًا من البنود السابقة دون نظام جديد.

---

## ٥. حدود هذا التقرير

- **كل البنشماركات المنشورة من جهات لها مصلحة:**
  - Qdrant تقيس Qdrant.
  - Zilliz ترعى VectorDBBench.
  - Tiger Data تقيس pgvectorscale.
  - لا يوجد بنشمارك مستقل حديث يجمع الست بنفس العتاد. الأرقام تصلح للاستئناس فقط، والقرار يُبنى على قياس على بياناتنا.
- **أسعار Qdrant Cloud غير منشورة رسميًّا.** وأسعار Weaviate لكل بُعد «تبدأ من»، والرقم الفعلي من الكونسول.
- **لم أجد بنشماركًا منشورًا لـ Chroma** في المصادر المعروفة.

## المصادر

- pgvector: [GitHub README](https://github.com/pgvector/pgvector) · [LICENSE](https://github.com/pgvector/pgvector/blob/master/LICENSE) · [إصدار 0.8.7](https://www.postgresql.org/about/news/pgvector-087-released-3392/) · [RDS و pgvector 0.8.0](https://aws.amazon.com/about-aws/whats-new/2024/11/amazon-rds-for-postgresql-pgvector-080/) · [pgvectorscale على RDS](https://repost.aws/questions/QUEgTTEzDeQdCoo5UJIEGAYw/add-pgvectorscale-extension-to-amazon-rds-aurora-postgresql-for-diskann-hnsw-hybrid-vector-search) · [pgvectorscale](https://github.com/timescale/pgvectorscale)
- Postgres والعربي: [Text Search Dictionaries](https://www.postgresql.org/docs/current/textsearch-dictionaries.html) · [Misraj: Full text search in postgres](https://misraj.sa/en/blog/full-text-search-in-postgres)
- أسعار RDS: [Bytebase](https://www.bytebase.com/dbcost/rds/instance/db.r7g.xlarge/) · [Vantage](https://instances.vantage.sh/aws/rds/db.r7g.xlarge)
- Qdrant: [GitHub](https://github.com/qdrant/qdrant) · [Pricing](https://qdrant.tech/pricing/) · [Benchmarks](https://qdrant.tech/benchmarks/)
- Milvus و Zilliz: [GitHub](https://github.com/milvus-io/milvus) · [Release notes 3.0](https://github.com/milvus-io/milvus-docs/blob/v3.0.x/site/en/release_notes.md) · [LF AI: Milvus 3.0](https://lfaidata.foundation/blog/2026/07/29/milvus-3-0-is-here-lf-ai-datas-open-source-vector-database-goes-lake-native/) · [Zilliz Pricing](https://zilliz.com/pricing)
- Weaviate: [LICENSE](https://github.com/weaviate/weaviate/blob/main/LICENSE) · [Pricing](https://weaviate.io/pricing) · [Pricing update blog](https://weaviate.io/blog/weaviate-cloud-pricing-update)
- Pinecone: [Pricing](https://www.pinecone.io/pricing/) · [Understanding cost](https://docs.pinecone.io/guides/manage-cost/understanding-cost)
- Chroma: [GitHub](https://github.com/chroma-core/chroma) · [Pricing](https://www.trychroma.com/pricing) · [System constraints](https://cookbook.chromadb.dev/core/system_constraints/) · [Groovy Web comparison](https://www.groovyweb.co/blog/vector-database-comparison-2026)
- البنشماركات: [Tiger Data: pgvector vs Qdrant](https://www.tigerdata.com/blog/pgvector-vs-qdrant) · [VectorDBBench](https://github.com/zilliztech/VectorDBBench) · [Zilliz Benchmark leaderboard](https://zilliz.com/benchmark) · [ANN-Benchmarks](https://ann-benchmarks.com/)
