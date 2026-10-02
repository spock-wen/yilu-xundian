# mobile/shared-test
独立 cjpm 测试模块,测试 mobile/shared 引擎与关卡数据(levels.json、boards-locked)。
运行:`cd mobile/shared-test && cjpm test`(约 10 秒)。
放在 mobile/shared/src 之外,故不会被 sync_to_keels.sh 复制进发布产物。
依赖 `yilu_zip = { path = "../shared" }`,只读引擎、不修改引擎代码。
