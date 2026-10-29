# مقارنة قواعد بيانات المتجهات — أكتوبر 2026

> تاريخ الجمع: 2026-10-29. الأسعار من صفحات التسعير الرسمية في هذا التاريخ ما لم يُذكر غير ذلك، وتتغيّر كثيرًا؛ راجعها قبل أي التزام.
> الأرقام المكتوب بجانبها **(تقدير)** حساباتي أنا، وليست منشورة من المصدر.

## الخلاصة

**التوصية: pgvector** (ومعه pgvectorscale إن احتجنا) على PostgreSQL، في **instance منفصل مخصّص للمتجهات** بذاكرة 32 GB تقريبًا.
تخزين المتجهات `halfvec` أو binary quantization مع rescoring، وفهرس HNSW.
التكلفة المتوقعة 350–410 دولار شهريًا على خدمة مُدارة (RDS أو Supabase)، وأقل بكثير لو استضفناه بأنفسنا.

**البديل الثاني: Qdrant** (Apache 2.0)، مستضاف ذاتيًا أو على Qdrant Cloud.
ننتقل إليه لو تجاوزنا ~50 مليون متجه، أو احتجنا QPS عاليًا مع فلاتر كثيرة وزمن p99 ثابت، أو صار الفهرس يضغط على قاعدة البيانات التشغيلية.

---

## 1. جدول المقارنة السريع

| | الترخيص | التشغيل | أرخص خطة مُدارة مدفوعة | أبرز عيب |
|---|---|---|---|---|
| **pgvector** | PostgreSQL License (مفتوح) | امتداد داخل Postgres؛ متاح على RDS/Aurora/Cloud SQL/Azure/Supabase وغيرها | تدفع ثمن Postgres نفسه فقط | HNSW يحتاج الفهرس في الذاكرة؛ الفلترة بعد الفهرس؛ VACUUM بطيء على HNSW |
| **Qdrant** | Apache 2.0 | self-hosted، أو Cloud مُدار، أو Hybrid/Private Cloud | Free دائم (1 GB RAM)؛ Standard بالساعة حسب الموارد، بلا رسوم على الاستعلامات | لا أسعار بالساعة منشورة (حاسبة فقط)؛ نظام جديد على التيم يحتاج تشغيلًا ومراقبة |
| **Milvus** | Apache 2.0 | self-hosted (Lite/Standalone/Cluster)، أو Zilliz Cloud مُدار | Zilliz Serverless بلا حد أدنى؛ Dedicated يبدأ من 16 دولار لكل مليون متجه شهريًا (capacity-optimized) | تشغيله ثقيل: etcd + object storage + Woodpecker؛ ويحتاج 16 GB موصى بها حتى للـ standalone |
| **Weaviate** | BSD-3 للنواة (وميزات enterprise تحت ترخيص Weaviate منفصل) | self-hosted، أو Weaviate Cloud (Shared/Dedicated/BYOC) | Flex من 45 دولار شهريًا + تكلفة حسب الاستخدام | HNSW في الذاكرة افتراضيًا؛ استهلاك RAM عالٍ في تقارير المستخدمين |
| **Pinecone** | مغلق (SaaS فقط) | مُدار فقط (serverless)؛ BYOC لعملاء Enterprise | Builder بـ20 دولار ثابت (حتى 10 GB)؛ Standard بحد أدنى 50 دولار شهريًا | لا تشغيل محلي؛ الاستعلامات مسعّرة بالـ read unit؛ يربطك بالمورّد |
| **Chroma** | Apache 2.0 | embedded، أو single-node self-hosted، أو Chroma Cloud | Starter بـ0 دولار + الاستخدام؛ Team بـ250 دولار شهريًا | الـ self-hosted عقدة واحدة بلا replication؛ والتوزيع الكامل متاح على Cloud أساسًا |

---

## 2. كل قاعدة بالتفصيل

### 2.1 pgvector (+ pgvectorscale)

- **الترخيص:** PostgreSQL License ([LICENSE](https://github.com/pgvector/pgvector/blob/master/LICENSE)). pgvectorscale من Tiger Data (Timescale سابقًا) تحت PostgreSQL License أيضًا ([repo](https://github.com/timescale/pgvectorscale)).
- **الإصدار:** صفحة المستودع تثبّت الإصدار `v0.8.7` ([GitHub](https://github.com/pgvector/pgvector)). وفي فبراير 2026 صدر 0.8.2 لإصلاح ثغرة CVE-2026-3172 (buffer overflow في parallel HNSW build)، فلا تستخدم إصدارًا أقدم منه.
- **التشغيل:** امتداد داخل Postgres؛ متاح على كل الخدمات المُدارة الكبرى. أما pgvectorscale فتوفّره خدمات أقل (على Tiger Cloud، والـ self-hosted).
- **الفهارس:** HNSW وIVFFlat. حد الأبعاد في الفهرس 2,000 لـ`vector`، و4,000 لـ`halfvec`، و64,000 لـ`bit`. أما pgvectorscale فيضيف StreamingDiskANN وStatistical Binary Quantization (SBQ) ([GitHub](https://github.com/pgvector/pgvector)، [pgvectorscale](https://github.com/timescale/pgvectorscale)).
- **التكلفة المُدارة:** لا تسعير خاصًا بالمتجهات؛ تدفع ثمن instance الـ Postgres:
  - RDS PostgreSQL `db.r7g.xlarge` (32 GiB): 0.478 دولار/ساعة ≈ **349 دولار شهريًا** on-demand ([reserver.io](https://reserver.io/reserved-instances/rds/db-r7g-xlarge)).
  - `db.r7g.2xlarge` (64 GiB): ≈ 698 دولار شهريًا on-demand، و≈510 بحجز لسنة ([Bytebase](https://www.bytebase.com/dbcost/rds/instance/db.r7g.2xlarge/)). الأسعار للحوسبة فقط، والتخزين والنسخ الاحتياطي منفصلان.
  - Supabase: XL (16 GB) ≈ 210 دولار، و2XL (32 GB) ≈ 410 دولار شهريًا + خطة Pro بـ25 دولار ([Supabase docs](https://supabase.com/docs/guides/platform/manage-your-usage/compute)).
- **الأداء المنشور:**
  - **Tiger Data — pgvectorscale مقابل Qdrant** (أبريل 2025؛ المصدر بائع لـ pgvectorscale): 50 مليون متجه Cohere بـ768 بُعدًا، على `r6id.4xlarge` (16 vCPU / 128 GB) للطرفين، مع binary quantization. عند recall 99% حقق Postgres **471.57 QPS** مقابل **41.47** لـ Qdrant 1.13.4. لكن Qdrant كان أفضل في الذيل: p99 بلغ 38.71 ms مقابل 74.60 ms. وبناء الفهرس استغرق ~11.1 ساعة مقابل ~3.3 ساعة، لأن بناء pgvectorscale يعمل على thread واحد ([Tiger Data](https://www.tigerdata.com/blog/pgvector-vs-qdrant)).
  - **pgvectorscale** يذكر في README الخاص به أن أداءه على 50M متجه مقابل Pinecone s1: p95 أقل بـ28 ضعفًا، وthroughput أعلى بـ16 ضعفًا، وتكلفة أقل بـ75% ([GitHub](https://github.com/timescale/pgvectorscale)). المقارنة مع نوع pod قديم لم يعد متاحًا للعملاء الجدد.
  - **The Build** على خادم صغير (2 vCPU، 3.8 GB، 1M×1536): DiskANN حقق p95 = 178.7 ms مقابل 1,603.8 ms لـ HNSW. السبب أن فهرس HNSW لم يتّسع في الذاكرة. والمؤلف نفسه ينصح بالبقاء على HNSW ما دام الفهرس يتّسع في الذاكرة ([The Build](https://thebuild.com/blog/on-pgvectorscale-and-hybrid-search-without-an-elasticsearch-sidecar/)).
  - **AWS Aurora:** على Cohere 10M (768 بُعدًا) مع binary quantization وإعادة ترتيب 3,000 مرشّح لكل استعلام، هبط الأداء إلى 16 QPS وp99 = 1,640 ms. الدرس: عدد المرشّحين في الـ rescoring مكلف جدًا ([AWS blog](https://aws.amazon.com/blogs/database/scale-pgvector-with-binary-quantization-on-amazon-aurora-postgresql/)).
  - pgvector موجود في [ann-benchmarks](https://ann-benchmarks.com/)، وغير موجود في لوحة VectorDBBench المعروضة.
- **الحدود المعروفة:**
  - الفلترة تُطبَّق بعد فحص الفهرس. فلتر يطابق 10% من الصفوف مع `ef_search=40` يعيد ~4 نتائج فقط، إلا إذا فعّلت `hnsw.iterative_scan` (متاح منذ 0.8.0، ومعطّل افتراضيًا، ويتوقف عند `max_scan_tuples=20000`).
  - VACUUM بطيء على فهارس HNSW. القيم NULL والمتجه الصفري (مع cosine) لا تُفهرس.
  - الفهرس المشترك بين عدة tenants يجعل بيانات tenant تؤثر على recall غيره ([GitHub](https://github.com/pgvector/pgvector)).
  - pgvectorscale يصف نفسه بأنه «still at an early stage»: لا يعمل على UNLOGGED tables، وقيم الـ labels محصورة في نطاق smallint، والترتيب relaxed ([GitHub](https://github.com/timescale/pgvectorscale)).
  - البحث النصي العربي المدمج (`arabic` snowball) ضعيف في التجذير، وهذا يهمّنا لو أردنا hybrid search ([misraj.sa](https://misraj.sa/en/blog/full-text-search-in-postgres)، [PG docs](https://www.postgresql.org/docs/19/textsearch-dictionaries.html)).

### 2.2 Qdrant

- **الترخيص:** Apache 2.0 ([pricing/FAQ](https://qdrant.tech/pricing/)). مكتوب بـ Rust.
- **الإصدار:** الخط 1.17.x (أوائل 2026): relevance feedback، وتقليل tail latency تحت الكتابة الكثيفة، وdelayed fan-out بين الـ replicas ([Qdrant 1.17](https://qdrant.tech/blog/qdrant-1.17.x/)). أما 1.16 فأضاف inline storage للبحث من القرص، وفلترة ACORN، وtiered multitenancy ([Qdrant 1.16](https://qdrant.tech/blog/qdrant-1.16.x/)).
- **التشغيل:** self-hosted (Docker/K8s)، أو Qdrant Cloud، أو Hybrid Cloud (إدارة Qdrant على بنيتك)، أو Private Cloud (حتى air-gapped).
- **التسعير المُدار** ([qdrant.tech/pricing](https://qdrant.tech/pricing/)):
  - Free دائم: 0.5 vCPU، و1 GB RAM، و4 GB قرص.
  - Standard: فوترة بالساعة على vCPU والذاكرة والقرص والنسخ الاحتياطي، و**بلا رسوم على عدد الاستعلامات**. لا أسعار بالساعة منشورة؛ الأرقام من الحاسبة فقط.
  - Premium بحد أدنى للإنفاق (SSO، وPrivate VPC، وSLA 99.9%). Hybrid وPrivate بالتفاوض.
- **الأداء المنشور:**
  - [Qdrant benchmarks](https://qdrant.tech/benchmarks/) (آخر تحديث 2024؛ قارن مع Elasticsearch وMilvus وRedis وWeaviate على عقدة 8 vCPU / 32 GB): يقول إن Qdrant حقق أعلى RPS وأقل زمن في معظم السيناريوهات. **والصفحة نفسها تقرّ بأنها «probably biased»**.
  - [VectorDBBench](https://zilliz.com/vdbbench-leaderboard) (من Zilliz، أي منافس): على Cohere 1M×768 وبميزانية ~1,000 دولار شهريًا، سجّل QdrantCloud-16c64g **1,242 QPS** وp99 = 6.4 ms، **وأعلى recall في الجدول (0.9474)**. وفي البث المستمر على 10M حافظ على أداء أكثر ثباتًا تحت الكتابة (446.9 ثابت ← 347.6 عند 1000 صف/ث) من Milvus (2,747 ← 156).
  - في مقارنة Tiger Data أعلاه: throughput أقل من pgvectorscale عند recall 99%، لكن p95/p99 أفضل، وبناء الفهرس أسرع بثلاث مرات.
- **الحدود:** نظام إضافي على التيم يحتاج مزامنة مع Postgres (dual-write أو CDC)، وbackup ومراقبة. وأسعار Cloud غير شفافة بدون الحاسبة.

### 2.3 Milvus / Zilliz Cloud

- **الترخيص:** Apache 2.0 (مشروع LF AI & Data). Zilliz Cloud هي النسخة المُدارة التجارية.
- **التشغيل:**
  - Milvus Lite للتطوير.
  - Standalone: 4 cores، و8 GB حدًا أدنى و16 GB موصى بها.
  - Cluster: 32 GB حدًا أدنى و128 GB موصى بها.
  - يعتمد على etcd وobject storage (MinIO/S3)، وWoodpecker كـ message queue مدمج منذ 2.6 ([Milvus docs](https://milvus.io/docs/prerequisite-docker.md)، [Woodpecker](https://milvus.io/docs/use-woodpecker.md)).
- **تسعير Zilliz Cloud** ([zilliz.com/pricing](https://zilliz.com/pricing)):
  - Free: 5 GB.
  - Serverless: 4 دولار لكل مليون vCU، و0.30 دولار/GB-شهر، بلا حد أدنى.
  - Dedicated (لكل مليون متجه بـ768 بُعدًا شهريًا): من 63 دولار (performance-optimized)، ومن 16 دولار (capacity-optimized)، ومن 5 دولار (tiered-storage). → 10M متجه على capacity-optimized ≈ **160 دولار شهريًا** (تقدير).
  - Enterprise من 197 دولار شهريًا.
- **الأداء المنشور:** [VectorDBBench](https://zilliz.com/vdbbench-leaderboard) (من Zilliz نفسها): ZillizCloud-8cu-perf حقق 13,316 QPS وp99 = 2 ms وrecall 0.938؛ وMilvus 16c64g مع SQ8 حقق 5,973 QPS. وفي اختبار Qdrant المنحاز بدوره: Milvus الأسرع في بناء الفهرس، لكنه متأخر في RPS عند الأبعاد العالية.
- **الحدود:** تعقيد تشغيلي واضح لفريق صغير. صورة `minio/minio` لم تعد تُسحب من Docker Hub بدون تسجيل دخول، وهذا كسر إعدادات compose القياسية ([PR مثال](https://github.com/mukoubuchi/vector-search-hands-on/pull/25)). وأرقام VectorDBBench تتطلب `force_merge`، وتنخفض كثيرًا تحت الإدخال المستمر.

### 2.4 Weaviate

- **الترخيص:** النواة BSD-3-Clause، وميزات `wl/` تحت «Weaviate License» ولا تعمل إلا بمفتاح مدفوع ([GitHub](https://github.com/weaviate/weaviate)، [Panoply](https://panoply.io/tools/weaviate/)).
- **التشغيل:** self-hosted (Docker/K8s)، أو Weaviate Cloud: Shared أو Dedicated أو BYOC.
- **التسعير المُدار** ([weaviate.io/pricing](https://weaviate.io/pricing)):
  - Free (sandbox).
  - **Flex من 45 دولار شهريًا** pay-as-you-go: الأبعاد «من» 0.00465 دولار لكل مليون بُعد، والتخزين من 0.12 دولار/GiB، وSLA 99.5%.
  - Premium من ~400 دولار شهريًا (SLA 99.9% أو 99.95%).
  - الخطط المدفوعة HA افتراضيًا، فتُضرب تكلفة الأبعاد في الـ replication factor ([PocketLantern](https://pocketlantern.dev/briefs/weaviate-ha-by-default-pricing-transition-october-2025)).
  - مثال تقديري: 10M × 1024 بُعدًا = 10,240 مليون بُعد × 0.00465 ≈ 48 دولار لكل replica. لكن مصادر أخرى تذكر سعر Flex غير المضغوط 0.01668 (≈171 دولار لكل replica)، أي أن السعر يتوقف على نوع الضغط ([RankSquire](https://ranksquire.com/2026/04/22/weaviate-cloud-pricing-2026/)).
- **الأداء المنشور:** غير موجود في لوحة VectorDBBench المعروضة. وفي Qdrant benchmarks (2024) هو «improved the least».
- **الحدود:** HNSW في الذاكرة افتراضيًا (~2× حجم المتجهات الخام قبل الضغط). وتقارير مجتمع عن 130 GB RAM عند 60M object ([Flur.ee](https://flur.ee/blog/weaviate-alternatives)، والمصدر منافس). ويوجد الآن فهرس قرصي HFresh وضغط RQ يقللان المشكلة.

### 2.5 Pinecone

- **الترخيص:** مغلق؛ خدمة مُدارة فقط. كل الفهارس الجديدة serverless، والحسابات الجديدة منذ 18 أغسطس 2025 لا تُنشئ pod indexes ([Panoply](https://panoply.io/tools/pinecone/)).
- **التسعير** ([pinecone.io/pricing](https://www.pinecone.io/pricing/)):

  | الخطة | الرسوم | التخزين | Write units | Read units |
  |---|---|---|---|---|
  | Starter | مجانًا | 2 GB | 2M/شهر | 1M/شهر |
  | Builder | 20 دولار ثابت | حتى 10 GB | 5M | 2M |
  | Standard | حد أدنى 50 دولار | 0.33 دولار/GB | 4–4.50 دولار/مليون | 16–18 دولار/مليون |
  | Enterprise | حد أدنى 500 دولار | 0.33 دولار/GB | 6–6.75 دولار/مليون | 24–27 دولار/مليون |

  تقدير طرف ثالث: ~70 دولار شهريًا لـ10M متجه على Standard، بحسب حجم الاستعلامات ([spendark](https://spendark.com/blog/vector-database-pricing/)). وتخزين 10M × 1024 float32 (~41 GB) يكلّف وحده ~14 دولار (تقدير).
- **الأداء المنشور:** VectorDBBench: Pinecone-p2.x8 حقق 1,146 QPS وp99 = 13.7 ms وrecall 0.926 على 1M. وهذا نوع pod، لا serverless ([VectorDBBench](https://zilliz.com/vdbbench-leaderboard)). ولا توجد أرقام مستقلة حديثة للـ serverless.
- **الحدود:**
  - لا نسخة محلية للتطوير أو الاختبار.
  - البيانات خارج Postgres، فيلزم الحفاظ على التزامن.
  - التكلفة تتصاعد مع عدد الاستعلامات (read units).
  - region الـ Starter مقيّد بـ AWS us-east-1.
  - ارتباط بالمورّد.

### 2.6 Chroma

- **الترخيص:** Apache 2.0. أُعيدت كتابة النواة بـ Rust في 2025، فتحسنت الكتابة والاستعلام 3–5 مرات ([Atlan](https://atlan.com/know/ai-agent/data-for-ai/what-is-chroma-vector-database/)).
- **التشغيل:** embedded داخل التطبيق، أو single-node server، أو Chroma Cloud (distributed مع SPANN/SPFresh).
- **التسعير المُدار** ([trychroma.com/pricing](https://www.trychroma.com/pricing)):
  - الكتابة: 2.50 دولار/GiB مكتوب.
  - التخزين: 0.33 دولار/GiB-شهر.
  - الاستعلام: 0.0075 دولار/TiB مفحوص + 0.09 دولار/GiB مُعاد.
  - الخطط: Starter بـ0 دولار مع رصيد 5 دولار، وTeam بـ250 دولار شهريًا مع رصيد 100 دولار.
  - تقدير طرف ثالث: 10M متجه (~29 GiB) بحجم استعلام معتدل ≈ 50–60 دولار شهريًا ([Markaicode](https://markaicode.com/pricing/milvus-vs-chroma-cost/)). والتحميل الأولي لـ~41 GiB وحده ≈ 100 دولار مرة واحدة (تقدير).
- **الأداء المنشور:** غير مدرج في ann-benchmarks ولا في لوحة VectorDBBench المعروضة. لم أجد بنشمارك مستقلًا معتبرًا.
- **الحدود:**
  - صيغة Chroma للذاكرة: N (ملايين متجهات بـ1024 بُعدًا) ≈ 0.245 × RAM بالـ GB. → 10M تحتاج ~41 GB RAM.
  - الـ self-hosted عقدة واحدة بلا replication أو failover.
  - تقييمات أطراف ثالثة تضع السقف العملي عند 5–10M متجه ([Atlan](https://atlan.com/know/ai-agent/data-for-ai/what-is-chroma-vector-database/)).

---

## 3. ملاحظة على البنشماركات

- **كل البنشماركات الكبرى منشورة من بائع:** VectorDBBench من Zilliz، وQdrant benchmarks من Qdrant (وتعترف بالانحياز)، ومقارنة pgvectorscale من Tiger Data. كلٌّ منها يفوز في بنشماركه.
- **[ann-benchmarks](https://ann-benchmarks.com/)** محايد نسبيًا، لكنه يقيس الخوارزميات على datasets صغيرة (≤1.2M)، لا الأنظمة تحت ظروف إنتاج (فلاتر، وكتابة مستمرة، وreplication).
- النقطة المتكررة بين المصادر: **الأداء يتحدد بأن يتّسع الفهرس (أو نسخته المضغوطة) في الذاكرة** أكثر مما يتحدد باسم قاعدة البيانات. لذلك لا بديل عن بنشمارك على بياناتنا نحن.

---

## 4. القرار لحالتنا

**المعطيات:** 5 مطورين، و~10M متجه لنصوص عربية وإنجليزية، وميزانية أقل من 500 دولار شهريًا، وPostgreSQL موجود أصلًا.

### 4.1 حجم البيانات (تقدير)

نموذج embedding متعدد اللغات بـ1024 بُعدًا (مثل BGE-M3 أو multilingual-e5-large أو Cohere embed-multilingual-v3):

| التمثيل | حجم المتجهات الخام لـ10M |
|---|---|
| `vector` float32 | ~41 GB |
| `halfvec` float16 | ~20 GB |
| `bit` (binary quantization) | ~1.3 GB |

فهرس HNSW على `halfvec` يضيف الـ graph فوق ذلك، فالمجموع في حدود 25 GB لكي يبقى «ساخنًا» في الذاكرة.
لو استخدمنا 768 بُعدًا (أو قصّرنا نموذجًا يدعم Matryoshka)، ينخفض كل ذلك بنحو الربع.

### 4.2 الاختيار الأول: pgvector على Postgres منفصل للمتجهات

**لماذا:**
1. **صفر نظام جديد.** التيم يعرف Postgres: النسخ الاحتياطي، والصلاحيات، والـ migrations، والمراقبة موجودة. مع 5 مطورين، تكلفة تشغيل نظام إضافي (Qdrant أو Milvus) أغلى من فرق الأداء.
2. **لا مزامنة بين نظامين.** المتجه في نفس الصف مع بياناته، فلا dual-write ولا CDC، ونحصل على transactions و`JOIN` وفلترة بـ SQL عادي.
3. **10M ضمن المنطقة المريحة.** بنشمارك Tiger Data أوصل Postgres إلى 471 QPS عند recall 99% على **50M**، فالحجم عندنا خُمس ذلك.
4. **الميزانية تكفي بهامش:**
   - RDS `db.r7g.xlarge` (32 GiB) ≈ 349 دولار + تخزين ~30–50 دولار.
   - أو Supabase 2XL ≈ 410 دولار.
   - أو self-hosted على VM مماثل بأقل من ذلك بكثير.
   - التخزين بـ `halfvec` يجعل الفهرس يتّسع في 32 GB.
5. **ترخيص مفتوح وقابل للنقل** بين كل مزوّدي Postgres المُدار، فلا ارتباط بمورّد.

**طريقة التنفيذ الموصى بها:**
- **instance منفصل** (أو قاعدة منفصلة على خادم مستقل) للمتجهات، لا على قاعدة الإنتاج الرئيسية. بناء فهرس HNSW على 10M وVACUUM عليه يستهلكان الـ CPU والذاكرة ويؤثران على الاستعلامات التشغيلية.
- عمود `halfvec(1024)` + فهرس `hnsw (embedding halfvec_cosine_ops)`.
  - إن لم يتّسع: فهرس HNSW على `binary_quantize(embedding)::bit(1024)` مع rescoring على المتجه الكامل لـ k×(5–10) مرشّحًا فقط، لا آلاف (راجع درس AWS أعلاه).
  - أو pgvectorscale/StreamingDiskANN لو كان المزود يتيحه.
- `SET hnsw.iterative_scan = relaxed_order` لأي استعلام فيه فلتر (لغة، أو tenant، أو تاريخ). وفهارس جزئية أو partitioning حسب اللغة إن كان الفلتر عليها دائمًا.
- **العربي:** جودة البحث هنا تأتي من **نموذج الـ embedding متعدد اللغات** أكثر من قاعدة البيانات. ولو أردنا hybrid (BM25 + vector)، فالـ `arabic` stemmer المدمج في Postgres ضعيف: نختبره، أو نستخدم hunspell، أو نعتمد على الـ vector أساسًا مع إعادة الترتيب بـ reranker متعدد اللغات.
- قبل الالتزام: بنشمارك صغير على عيّنة 1M من بياناتنا الحقيقية، نقيس recall@10 وp95 بالفلاتر التي سنستخدمها.

### 4.3 البديل الثاني: Qdrant

- **لماذا هو، لا الباقي:**
  - مفتوح (Apache 2.0)، فنستضيفه بأنفسنا بنفس الميزانية.
  - ونسخته المُدارة **لا تحاسب على الاستعلامات**، فالتكلفة متوقعة.
  - فلترة payload قوية (ACORN)، وbinary/scalar quantization، وinline storage للقرص.
  - أعلى recall في VectorDBBench، وأثبت أداءً تحت الكتابة المستمرة، وp99 أفضل من pgvectorscale في مقارنة Tiger Data نفسها.
- **لماذا ليس الأول:** نظام ثانٍ، ومزامنة مع Postgres، وخبرة تشغيلية جديدة على فريق من 5 أشخاص.

**لماذا استبعدنا الباقي:**

| القاعدة | سبب الاستبعاد |
|---|---|
| Milvus | تشغيلها ثقيل لفريق صغير، ومصممة لمئات الملايين والمليارات |
| Weaviate | استهلاك ذاكرة أعلى، وتسعير Flex حسّاس للضغط والـ replication |
| Pinecone | لا تشغيل محلي، وتسعير بالاستعلام، ونقل البيانات خارج Postgres بلا مقابل واضح عند 10M |
| Chroma | الـ self-hosted عقدة واحدة بلا HA، و10M عند سقفها العملي تقريبًا |

### 4.4 متى نغيّر من pgvector إلى Qdrant

نراجع القرار عند تحقق أيٍّ مما يلي:
1. **الحجم:** تجاوز ~50M متجه، أو نمو متوقع إلى 100M+، والفهرس المضغوط لم يعد يتّسع في instance بحدود الميزانية.
2. **الزمن تحت الحمل:** p99 فوق الهدف (مثلًا >100 ms) عند QPS مطلوب (مثلًا >300–500) رغم الضبط (`ef_search`، وBQ، والذاكرة).
3. **الفلاتر:** recall يهبط بوضوح مع الفلاتر رغم `iterative_scan` والفهارس الجزئية، خصوصًا مع فلاتر كثيرة الانتقائية أو متعددة الحقول.
4. **الكتابة المستمرة:** إدخال/تحديث كثيف (آلاف الصفوف في الثانية) يجعل صيانة HNSW وVACUUM مكلفة.
5. **العزل:** multi-tenancy بأعداد كبيرة يحتاج عزل recall بين العملاء، وقد صار الـ partitioning في Postgres غير عملي.
6. **التشغيل:** بناء الفهرس أو إعادة بنائه (مثلًا عند تغيير نموذج الـ embedding) صار يستغرق ساعات تعطّل العمل، بينما Qdrant يبني أسرع بنحو 3 مرات في بنشمارك Tiger Data.

وإن قرر التيم لاحقًا أنه لا يريد تشغيل أي شيء بنفسه، فـ Qdrant Cloud أو Zilliz Cloud (capacity-optimized ≈160 دولار لـ10M) خياران مُداران ضمن الميزانية.

---

## 5. المصادر

**صفحات رسمية**
- pgvector — https://github.com/pgvector/pgvector
- pgvectorscale — https://github.com/timescale/pgvectorscale
- Qdrant Pricing — https://qdrant.tech/pricing/
- Qdrant Benchmarks — https://qdrant.tech/benchmarks/
- Qdrant 1.16 — https://qdrant.tech/blog/qdrant-1.16.x/
- Qdrant 1.17 — https://qdrant.tech/blog/qdrant-1.17.x/
- Milvus requirements — https://milvus.io/docs/prerequisite-docker.md
- Milvus Woodpecker — https://milvus.io/docs/use-woodpecker.md
- Zilliz Pricing — https://zilliz.com/pricing
- VectorDBBench Leaderboard — https://zilliz.com/vdbbench-leaderboard
- Weaviate Pricing — https://weaviate.io/pricing
- Weaviate pricing update — https://weaviate.io/blog/weaviate-cloud-pricing-update
- Weaviate GitHub — https://github.com/weaviate/weaviate
- Pinecone Pricing — https://www.pinecone.io/pricing/
- Pinecone cost docs — https://docs.pinecone.io/guides/manage-cost/understanding-cost
- Chroma Pricing — https://www.trychroma.com/pricing
- Supabase Compute — https://supabase.com/docs/guides/platform/manage-your-usage/compute
- PostgreSQL text search dictionaries — https://www.postgresql.org/docs/19/textsearch-dictionaries.html

**بنشماركات وتحليلات**
- Tiger Data, Pgvector vs. Qdrant — https://www.tigerdata.com/blog/pgvector-vs-qdrant
- The Build, On pgvectorscale — https://thebuild.com/blog/on-pgvectorscale-and-hybrid-search-without-an-elasticsearch-sidecar/
- AWS, pgvector binary quantization on Aurora — https://aws.amazon.com/blogs/database/scale-pgvector-with-binary-quantization-on-amazon-aurora-postgresql/
- ANN-Benchmarks — https://ann-benchmarks.com/
- Nile, pgvector 0.8.0 — https://www.thenile.dev/blog/pgvector-080

**أطراف ثالثة (للأسعار والحدود؛ أقل موثوقية)**
- Bytebase RDS r7g.2xlarge — https://www.bytebase.com/dbcost/rds/instance/db.r7g.2xlarge/
- reserver.io RDS r7g.xlarge — https://reserver.io/reserved-instances/rds/db-r7g-xlarge
- PocketLantern, Weaviate HA pricing — https://pocketlantern.dev/briefs/weaviate-ha-by-default-pricing-transition-october-2025
- RankSquire, Weaviate pricing — https://ranksquire.com/2026/04/22/weaviate-cloud-pricing-2026/
- Panoply, Pinecone — https://panoply.io/tools/pinecone/
- Panoply, Weaviate — https://panoply.io/tools/weaviate/
- spendark, Vector DB pricing — https://spendark.com/blog/vector-database-pricing/
- Atlan, Chroma — https://atlan.com/know/ai-agent/data-for-ai/what-is-chroma-vector-database/
- Markaicode, Milvus vs Chroma cost — https://markaicode.com/pricing/milvus-vs-chroma-cost/
- Flur.ee, Weaviate alternatives — https://flur.ee/blog/weaviate-alternatives
- misraj.sa, Postgres FTS (Arabic) — https://misraj.sa/en/blog/full-text-search-in-postgres
- Milvus standalone without MinIO (PR) — https://github.com/mukoubuchi/vector-search-hands-on/pull/25
