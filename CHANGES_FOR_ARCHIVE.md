# Files changed for the archive

Almost every archived file is a byte-for-byte copy of its file in the project. This file lists every archived file
whose bytes differ from its source: 163 files, as listed on 2026-11-23 at 03:14 UTC. For each it gives the change,
the number of replacements, and the SHA-256 of the source and of the archived copy. Two changes are made, and only in
files whose bytes no recorded hash covers; the files whose SHA-256 a table, lock, manifest or record gives (those of
Supplement S4 among them), the dataset packages, the hashed folders of the code versions and the run records are
copied unchanged.

- **Name cleaning** (116 files, 5,835 replacements). The user name, in every written form, is replaced by `<user>`;
  folder names built from the profile path, and some other identifiers, are replaced in the same way by other
  placeholders in angle brackets.
- **De-quote** (54 files, 264 replacements). Where a record quoted the author's answers word for word, the quotation
  is replaced by a plain description of the answer, for example that the author accepted every recommended answer or
  chose option (b). The questions put to the author, the options offered but not chosen and the records' own terms
  stay as written. The replaced words are not repeated here.

Both changes stay inside a line. The encoding, the byte-order mark, the line endings and the number of lines are
kept, and every byte outside a replaced span is unchanged, so line numbers cited elsewhere still hold. Of the 163
files, 7 have both changes; in them the de-quote is made after the name cleaning. A few sentences of the de-quoted
records still say that the record quotes the author's words (for example rulings AV5 and BC8 in
`engine/OWNER_RULINGS_2026-10-06.md`); in the archived copies those quotations are the plain descriptions.

A few hash-locked records (the signed pre-registrations, sign-off records, protocol snapshots and dataset-package
comments, and a few comments and notes in hash-locked code, tool versions and run records) keep their text as
written, including short approvals by the author, so that their fingerprints can be checked. [OWNER: confirm that
these files keep their text]

Some de-quoted tool outputs and scripts therefore no longer match text written elsewhere: the coral signing outputs
and the approval string of the product fetcher differ from the text that the same tools wrote into hash-locked files,
which keep the original wording, and the quote check of one table-build script would no longer pass if it were run
again.

The frozen fact sheet, `records/fact_sheet/PAPER_FACTS.md`, is one of the de-quoted files: the SHA-256 of its source
is `344c581d518a851615b8a8dcfa64753ed0b957499ba1e91268feb8dc2063002a`, and that of the archived copy is
`d3f6cc53c73728eeeed3df919eadba7c07f2d0b4b56a26aa38a5ccf8d52f15a7`.

Files written for the archive have no source file and are not listed here: the root files, `engine/README_ARCHIVE.md`
and `engine/tests/STALE_TESTS.md`, the dated notes beside the four gridded protocol copies, `VERIFY_HASHES.py` and
the written-out code versions of `VERSIONS.md`. `SHA256SUMS.txt` gives the SHA-256 of every file.

| Archive path | Change | Name replacements | De-quote replacements | SHA-256 of the source | SHA-256 of the archived copy |
|---|---|---:|---:|---|---|
| `analysis/common_table.py` | name cleaning | 1 |  | `5de61d11704eb0b83ede96055482ba1dc9e4ec1c8ecf0c07786f7578b6b8ed6b` | `2ec23a138e3f11c4e6b1651cfcda98328b171c9e3a62d791dd2e0dd0251e60b9` |
| `analysis/coral_choice/drift/scripts/rebuild_weights.py` | name cleaning | 1 |  | `360ffe783b9734a6416c3e87531bf0e00f84ce477f9d1a87d25d2c044aba2e65` | `4b4b71725e2e099b9cdeac26e37e7eb41a14a666e2521da1ebe007b682c3ef94` |
| `analysis/coral_choice/explain/rules_check.py` | name cleaning | 1 |  | `f85fe68049013b02d8aca06074b85bdb43ee8a06844b861948e07c80a397dc7c` | `63f95f32c8a41552b0cdbe22093feaa09530bc2c60e35130a3c0f4b6ca51144f` |
| `analysis/coral_choice/EXPLANATION.md` | name cleaning | 1 |  | `bd89059daf7693c5d882aff5618b7004e8825ea68a20e27830cdbba9e6245b5e` | `04d76960acb1c6ead0cc57596e478a3f80305c73ad02351f79c33fd544e1bad4` |
| `analysis/coral_sens_2017_2020/coral_data/full/build_manifest.json` | name cleaning | 5 |  | `8d4f89a19eb27583091e6e3157f61f876f78fef364bd4e5251d086dc800d4dbe` | `4e47abcd7f0a24495c24db404b8dec17fef5048c3a50ddf72359f6be09f220c7` |
| `analysis/coral_sens_2017_2020/logs/compare_hashes_after_run.log` | name cleaning | 5 |  | `68b49de454af27549015e568b5135678119debf6e35d7347875b4526b2ccc8d6` | `352302cc15ca49f997e4503455ec221b727ce60ce6405a1c10231a296864d2ce` |
| `analysis/coral_sens_2017_2020/logs/engine_run.log` | name cleaning | 2 |  | `1622c996347760da9dd5e47d51d73904fcd9f27630587e4faa34996ecf0f0b7d` | `f83b82a3b360e425830dd27ee516250502a408828fe00279924a5f9f8c687d09` |
| `analysis/coral_sens_2017_2020/logs/hash_after_run.json` | name cleaning | 5 |  | `13a492c931f5072fa86df2c65036f678613e1892d962ff29c08b3d0e311d479f` | `a881be15b88eb72e9217504d9d66efc3310ea93fbc5dc3140bb9e9aadb8a4e86` |
| `analysis/coral_sens_2017_2020/logs/hash_tree_after_run.log` | name cleaning | 5 |  | `ca67b35be56d0078dd33561344ee6937c8a42e9e32b59a402d060eb3b5a18fcd` | `634a83d514a67a75260720672c4ef010f4353eac885a30a13734faa4c82e6015` |
| `analysis/coral_sens_2017_2020/validate/compare_hashes.log` | name cleaning | 5 |  | `4d1768967f36df31000054ee603a6de6f0d4cef9a0dbefc0e7d31ce4e2555207` | `6796833ea42bf0a76f18df2739f74c71d94ad8ef0f01a1a378a13019cd784a11` |
| `analysis/coral_sens_2017_2020/validate/hash_after.json` | name cleaning | 5 |  | `13a492c931f5072fa86df2c65036f678613e1892d962ff29c08b3d0e311d479f` | `a881be15b88eb72e9217504d9d66efc3310ea93fbc5dc3140bb9e9aadb8a4e86` |
| `analysis/coral_sens_2017_2020/validate/hash_before.json` | name cleaning | 5 |  | `13a492c931f5072fa86df2c65036f678613e1892d962ff29c08b3d0e311d479f` | `a881be15b88eb72e9217504d9d66efc3310ea93fbc5dc3140bb9e9aadb8a4e86` |
| `analysis/coral_sens_2017_2020/validate/load_check.log` | name cleaning | 1 |  | `74a082ec63158cc6011e1273a9af77ee684c269ef0cbd99d9d3402020a3bce7b` | `8085ed78e70e2004d807232c24f2a09e977b09502f1ee4b29b9e1ae67b354aec` |
| `analysis/coral_sens_2017_2020/validate/plan_root/coral_sens_2017_2020/headline/20261028_71d8df79/manifest.json` | name cleaning | 1 |  | `a77f6ab84a1398f327223ed71fed5acfb6f80360eb8e918acdef1d450d60afda` | `d54d2b4b3328615b3488577671a5cfff29701428d4c74a79391dddc2843f7e75` |
| `analysis/coral_sens_2017_2020/validate/probe_smoke_fulldeep.log` | name cleaning | 1 |  | `753098923e7f58fb63a3f622d991ce9f0f9238184952cef44a127ac1e92a7b54` | `1009047ec4c5896569d99dbc3f0de9644e9456c27f7740460574a5c36afa6da9` |
| `analysis/coral_sens_2017_2020/validate/settings_diff.txt` | name cleaning | 2 |  | `8d7a4d281884ea70d14755fd8d136d98fe7418411bfa86e64e0b5beef9a75b34` | `8a59d7ef3eb4ac8e6ad0b8cb972122e6bb06b2f07b410340af22d4dffd9e0393` |
| `analysis/coral_sens_2017_2020/validate/tiny_check/tiny/build_manifest.json` | name cleaning | 5 |  | `56c0df6f8ee062b3d86181a5aceadec160dee4c142cabe9649ffdb732c3b2eed` | `a151a6ed34fff2e5da319e1bc6d1356605fd6a0cccf3ee1817d6eb98855e61e4` |
| `analysis/final_table.py` | name cleaning | 1 |  | `eb517257629abb45f23e7e4e26e46b8d413fbc603839868b6389583f180631f9` | `46866d98b5ce2b8bff9bbbd45de3e7c36ab1bde8c8fed19666133a562a290fe1` |
| `analysis/guidance/coral/scripts/stage_a.py` | name cleaning | 1 |  | `85ff02d4b810675588dfe24e0d2f68a6b7c8d6bf913125da5aceae9efd49dce3` | `fb33775aaf4b499f8214b77ad32d7e520071062159da4ce534bcdb3ed0770169` |
| `analysis/guidance/ndvi/stage_a.log` | name cleaning | 12 |  | `ca5066a61bfe5691fb94068148dac97d3254429f7612e38c61711978ea99595f` | `8db4ae8591a87086415b55aaed5e8e3bfa336374338f93a557ce4262c19286d5` |
| `analysis/paper/figures/fig1/fig1.py` | name cleaning | 1 |  | `44288baff779a46994aca1c54b3582c0591c932ff7b55ce6bf808d91caafd0d2` | `8a4e54e501454c1248a2de185a218509f1496fe26fbb44f4ccd6132c264b9fba` |
| `analysis/paper/figures/fig1/fig1_data.csv` | name cleaning | 76 |  | `95395ba105a9898e26a5a0d5ce2f23f893654c91c80312d3a743871cfd30a539` | `56be5709a7626dcfa4ccbbc1534144c7a29883036a6933f306108325f949a2cf` |
| `analysis/paper/figures/fig2/fig2.py` | name cleaning | 4 |  | `38b90f0e0ab09b46f4034472c414dc309e45c3aee43369cb2f2811e444ad2520` | `6a2cc32f4315ca7cdca4fb34d954ba1e5dc553f7e1f238667dfbf354e3789f3b` |
| `analysis/paper/figures/fig2/fig2_data.csv` | name cleaning | 4 |  | `85b62818a53659cd04d4ea50d179393a4757118ce3b4da3c485ad773bd33c962` | `2130cf995fb40f774f5a0f060b307811bfa1cfa72bdfcd0da7cbcf1e6d1f9be0` |
| `analysis/paper/supp_build/s3_13/checks/recheck/b07_out.txt` | de-quote |  | 5 | `d365db5e11de16dc29154845bc5fa8b2bde344a8769b3b90756b63028d9e3790` | `55acdab795bde74534303bb3f96cac032aab9a93d1df059335cb5abfb1121d35` |
| `analysis/paper/supp_build/s3_13/writeup/_scripts/fix/apply_fix.py` | de-quote |  | 1 | `7d8a6665327b77f63794f633ac1398e3bf0cf479ebb3a5ac22ae23f37532421a` | `15c29c833937dbe7cb8e5e666a727257d802d03ea1d6bf01fc2849c5bca12a82` |
| `analysis/paper/supp_build/s3_13/writeup/_scripts/fix/work/applied_edits.json` | de-quote |  | 1 | `fd04697468a89377950f9d0b70b2d16cbc14908461dc1c40a6513f357c3c4819` | `99d44f7c3ca1e5bbe03aebfc1bb37356f4c8642e466606e2a0a35ab3d7a7abbd` |
| `analysis/paper/supp_build/s3_13/writeup/_scripts/records/texts_pending.py` | de-quote |  | 4 | `cd6b91cab0fdd6969f42fbd01570b9ea212883053283bf1167d7438a8f199ae2` | `dd3088376ef321a27f272d33a56c58e7e8ffa56a3498afe0b8c133a5dadd5bb1` |
| `analysis/paper/supp_build/s3_13/writeup/_scripts/s1s4/build_s1s4.py` | de-quote |  | 28 | `169e3adf975d1fdd73731f195046fef67fb3f377965fa51dd07a4974e12a8116` | `be46655a4f4602b84d033a98c3d4e511962aa45cf4a5b8d70b709e76ea4be51b` |
| `analysis/paper/supp_build/s3_13/writeup/changes_fix.md` | de-quote |  | 1 | `2754f1c17c7eccac9a62770fa2515976e49c6b4f71bee08fc87766022135866d` | `e3122d5d323be3f5e3c7c14fceaa086016d8d1dd53a028659fe6bbbc6ffed596` |
| `analysis/paper/supp_build/s3_13/writeup/changes_s1s4.md` | de-quote |  | 1 | `b289c47e44c5c0039b8016e4c7dab30a1c5b9b9c216aa99546b7165818eca88b` | `fa7651f7bbb137090e6e89e21579babd9c8b9d80d6b06bc092a3a366efff0ba4` |
| `analysis/paper/supp_build/s3_13/writeup/changes_s3.md` | de-quote |  | 1 | `4616cb9931786f7bef1299856a706f9527549dffbdde8fb9e0b79f70f9488e41` | `83b673b6278b1611d5c3649068cd4974362c96694d4bc5234088ab8e59f77e3a` |
| `analysis/paper_posthoc/_probe/gen_spec.py` | name cleaning | 1 |  | `c93cfe3b8aa49e98f800ef08c65ff9b7e50ff079b7583c23df98a7f1dd26a142` | `ad190e1ce6d5bac06f89b26e990d016aa05cb3433609f6dec94f5068409d3e7c` |
| `analysis/paper_posthoc/merra2_formula/A/rescore_A.stdout.txt` | name cleaning | 1 |  | `b03d9737281ae59c26e1db446c3c687e1a8fb787c5e0b84d7f20441f36a13b33` | `9365117cf40d12e15341a6569838d45233523d80bcfbe58c400f3acc5f385eb7` |
| `analysis/pm25_ridge_audit/RESULT.json` | name cleaning | 39 |  | `53134c2e6af7e08431b2e2363f0178c0c0e4c5b2162e0ba23a3f4c06122ff1fe` | `6e6d04fb5cdd158e6145b560044250d8a60821f731ddc850488668d0dad952d0` |
| `analysis/pm25_ridge_audit/scripts/ban_cmp.py` | name cleaning | 1 |  | `61872b239f23cf3d2dde8e2e9ec4ff632e791e237c16294bbf8635ffec6b04fa` | `fed7255060c44d0950862d433c54acb05ff969895f74ff61f974a0e759e9ffe7` |
| `analysis/pm25_ridge_audit/scripts/fair_cols.py` | name cleaning | 1 |  | `3e93917e385d3c481de91ab4f4cd2a29c8287757446167ed2cf02b62d3fd02c6` | `d5931293ed135dc33d4311ad5cf221558e399b8f8c6a926db24a0cc41ca2fd94` |
| `analysis/pm25_ridge_audit/scripts/inner.py` | name cleaning | 3 |  | `c10c6821e9a5ef2d2616abfc055c543ea3532ae5fe990961cb534e5eed74a5a2` | `c57e5d426cc6bfa43cd604a448984790ffe50ae554bb79f946c399a3c88e9f2a` |
| `analysis/pm25_ridge_audit/scripts/ridge_audit.json` | name cleaning | 39 |  | `53134c2e6af7e08431b2e2363f0178c0c0e4c5b2162e0ba23a3f4c06122ff1fe` | `6e6d04fb5cdd158e6145b560044250d8a60821f731ddc850488668d0dad952d0` |
| `analysis/pm25_ridge_audit/scripts/ridge_audit_summary.txt` | name cleaning | 12 |  | `06800a7cc9e7a2320d843d3ae04f422b06b5ee760aa9017c238e8ca6c932f385` | `431b882bcb95f69f6ab702bff98a485a2d100db2428f5399ecd1862d0bb14268` |
| `analysis/pm25_ridge_audit/scripts/trend.py` | name cleaning | 3 |  | `05f26590b319c8773a9bf9e0ca056eda3862e7ce0fdfa210fc9abcbd5391b9aa` | `e29148953f63808a6328677defaf1b9d208bd5fe537e3177d9760ad9342a780d` |
| `analysis/pm25_ridge_audit/SUMMARY.txt` | name cleaning | 12 |  | `6652d64b62873417e1288abb647a3e81dadef4a746cdf93ff4eac586a31b60a5` | `7f5b0909231d388544236690b0044c476af4daba7186ee8bcbafcbadc2590bd6` |
| `analysis/shap_v1/PROTOCOL.md` | de-quote |  | 11 | `6f219c994691352356aa876f896ef1b4f766785f6056036268d1e6bf90d4e04f` | `8da144bc7649cfa7165b3e50b41c7ae7c2480f69f743b39051c40fc415afa567` |
| `coral_build/fullsuite2.log` | name cleaning | 3 |  | `1c8d95bcaeeed05d4af0280ed4c3f9a3acede5a74c7ea7be6f0ccf6a617b9bfb` | `8b8647fafa86bdc1c1f2e27d10c9f2d7377d47d7fbba7d7ec87fca79e739416e` |
| `coral_build/fullsuite_20261019_233358.log` | name cleaning | 920 |  | `7b8fca9ee4b87331ab6da6a944e9ad45e8317dc9d20d792b63a466419dad8b12` | `69710a16102fda4d9b9a23e339f1dde31895febd0bb21217a24b7b2711b04eb2` |
| `coral_build/live_smoke.log` | name cleaning | 2 |  | `e002fa4a7ec65a79d9480913d7c0761e7515f737af6b5d773d9df9527af7113d` | `815459b95289251c453f9b0a80aedd86009c7bc95eabe8d259de9511b706fb60` |
| `coral_build/PLAN_RULING_V.md` | name cleaning | 1 |  | `34a76ae34c6415d08bdac6cf2f156c79321429813cf00499dd746c3e8d652e4d` | `569638dd22928e332a64f68cacc7287cf92151c28175b13357bf66f5042f3f1c` |
| `coral_build/PREREGISTRATION_DRAFT_coral.md` | de-quote |  | 14 | `bc070143c70a2d43962330ef6aad8e6c770dd13fc324e9b57b85ce0f309d6e2f` | `11cdbd5510f4ee6b8c3a366297827ac42278216a5ee2463db542718e2f3f4278` |
| `coral_build/report_scripts/toy_runs/donor_only_group/runs/toy_table/smoke/20261020_9db32590/manifest.json` | name cleaning | 1 |  | `b9e7c9af1e7e9d6b4dbc88d16fd3173588e3fa59496035e0e8d6036ede198aa5` | `ae5f43ec236858ac47fc08a15cad8f9daa59535cd88cac861f2e2dfda005a77f` |
| `coral_build/report_scripts/toy_runs/ok/runs/toy_table/smoke/20261020_603d4728/manifest.json` | name cleaning | 1 |  | `8ce9f161abfefd1dadc9755f448380f36600a4650015351aa4bd1678ba90af66` | `1450c43a6e65c7efbcf8a030c19bd2a57f7605d7999f99a76a8de8a8baa93002` |
| `coral_build/run_noop_proof.ps1` | name cleaning | 1 |  | `81ca6e623138b1e99dd2ac63fac0dcea2e6ff088d43b74d01e7b3904641bdea0` | `a78832c67729c0a47759ae88dc0a0249ec3bcb1c8a76ec7905e49a8bb4931c3f` |
| `coral_build/SPEC_CORAL_TABLES.md` | name cleaning | 1 |  | `a4ad27baf221247376517e1b0d5c38e5b06d43ea69b0ee5a60730da940624a75` | `882b1de5378dea0dd352f02c118ddbe441b75f3d0ee3a18b2fe1b52a81ce044d` |
| `coral_build/SPEC_NEIGHBOUR.md` | name cleaning | 1 |  | `ee782e294daeb4ad9165a2bf83c74404766a7d349e46f9e12bd9fc171501c014` | `01574bb4e479410dd924b4bb4faf6a2502a0d4f909e8e6c8a1d7b38628842977` |
| `coral_build/tools/install_into_live.py` | name cleaning | 1 |  | `0415230849d3e32a579048d5865773c314807e117cc2402db4450e153cb2800d` | `9f402e51865a45935f7619d870b3ebbd061292c1d75729007a9c7a621e80a959` |
| `coral_build/tools/signing_apply_2026-10-20.txt` | both | 3 | 2 | `b95bf2ad2a0a6a22307d724a3a433f2621d5e69cd68f65f4716d5ea27ab87d8a` | `28bca46b85f593d7f3c6706403c25d534203704fb6822653cfe0ab8c8356a438` |
| `coral_build/tools/signing_dryrun_2026-10-20.txt` | both | 3 | 2 | `fcd6224f0a6e28a726206f912a29d8bd9752498f7b3b79a260a45f374823e12b` | `761eb2c811836adb908a3773b155333e1cf46153946529c642151640e21dc869` |
| `coral_build/tools/signoff_records/coral_signoff_record_20261020_130714.json` | both | 2 | 1 | `18ad108e4605ffeb325fb99000da4c607980724d1fb9054e2b09efcbf3026e77` | `27ba1ba8ef3f6a8ee9709de708992deedf641180ab7296901aae529348e9b47d` |
| `engine/CORAL_ENGINE_PLAN.md` | name cleaning | 2 |  | `6a93b38b3d662717dc2b4448a8bd1af012aa0537ce714f8841a3271788d285d5` | `157989915d7839471d64a61e7f6501d13071c68ae0f1c564c501908270d347df` |
| `engine/datasets/_stores/index_facts.yaml` | name cleaning | 2 |  | `65b1258ba3c1aa749a4d528efe6d167d607361dce096cf28df53a7c0127dcffd` | `c8e264148f35f898fea47b0f1634bbfd20e9136bfcb14279430c710370fc0a99` |
| `engine/datasets/_tools/apply_signoff.py` | name cleaning | 1 |  | `3b4523dad5dda862f1bb489c8c34868b86b4214b4e2e3f8e3dadbe07e011bad9` | `07e6dd70974a70813dd7ebbf3d8a677b9d7e6cd2ebfe54cc154a392aff2da8df` |
| `engine/datasets/_tools/refresh_drafts.py` | both | 1 | 1 | `9f5cb7f6dd05748f69759044191cdc68a7d77f73a4ef87bc463b258dd08d84e7` | `b3e2d45f49d9ce4dfc8a430d08508cadd66bb6335f73c85132daa08b5afa8567` |
| `engine/datasets/_tools/signoff_answers_2026-10-06.yaml` | de-quote |  | 1 | `a335cc893be51bf59b5d181a50d3e36814d92a3884a4cb3090b6e54747be7d1a` | `44b887c27281a1dbc675dfb887c3038a93db8c26422ed605715ced3125b1d0a5` |
| `engine/datasets/review/PENDING_DEFO_L.md` | de-quote |  | 2 | `7867e4a528c978a1bb93317049d7212c66c8d15db303740a860be0d020b29e52` | `5c75ecacc44178f99b4a99bd48b4a68b9c35840ebf5c9c4f4ebe0254a2e54636` |
| `engine/datasets/review/proposed/BAN_REVIEW_SUMMARY.md` | de-quote |  | 1 | `0f270f37b4d62c4cd7691801d897adb1fc55eafd60500c35a7beaf67d9c486c5` | `3e3a58b479fb29554018560b1ff907e48a414b83fa3a4dd5ce83033ae09b335c` |
| `engine/datasets/review/proposed/defo_ban_proposed.yaml` | de-quote |  | 1 | `54ed0a4fe6a47cbbb31d1168d3faba6b997ee9ff7516f9f983dd249b1958013e` | `e7b4297702123a6346112fd71496392fe0d560186ec6ed0e3960ca9e061ee46a` |
| `engine/datasets/review/proposed/ndvi_ban_proposed.yaml` | de-quote |  | 1 | `eae4db0b7b95a06a6291005cbcbb5889ec5db49b59771ffc0072b63dac4c8a7c` | `8ec06b0462581895b5eb78a4947249121b2d065c10d79471e342cd9b4b848498` |
| `engine/datasets/review/proposed/pm25_ban_proposed.yaml` | de-quote |  | 1 | `9b45f9c911bfa820f4daefe82278c2497a7bc16efd386c89625dfaedda29f369` | `25d1a5fe0ede0460f8a57097896f8730b6cff05cbf90f677234e459750b630d4` |
| `engine/L_REPORT.md` | de-quote |  | 1 | `7f855d1d51db162c1af36602de3cc38a56119e301cb661914598a7bc6c58f42c` | `a752515872df2eea98c89cc10cbe3b01e05f307236292e7deb7f8b4bd9af23db` |
| `engine/legacy_harness/bank_replay.py` | name cleaning | 1 |  | `f29478fd8409336cd69a55dd6a2a0757f8f8f56549013c2fb4dcb83959e49c0f` | `517f2ccdfb4c885b6bdb5fb0e1f36efa1040f3800e41b6f7b82d43c984abc903` |
| `engine/legacy_harness/goldens_v3.json` | name cleaning | 18 |  | `de311490f1bfafa3f1aa0fa1dc71c90d7a9f0d27d871263431efc3c1a1a1ce16` | `4f2eaa095a10bfe1baf91e3b8a2e1f8c9c86f0c362d0f6d2e99f52d4e3773e1a` |
| `engine/legacy_harness/layer_replay.py` | name cleaning | 1 |  | `87bff54a18bf12c06da826e23caea4047da6f87cc68477cfb204fd782229dcdb` | `4d194d23103b91e3fd6d3ebf4f4bea5e34795e7589512426f81e1e7a9dd830f9` |
| `engine/legacy_harness/README.md` | name cleaning | 2 |  | `626e3944db398b982ffd93db8207ddc08798153860f94c73523d15876747db30` | `0edb2fe94582ec6bc2219c2a03a70a8b005a04de610e94c4d08face5c83b57c4` |
| `engine/legacy_harness/region_replay.py` | name cleaning | 1 |  | `d4c37a9693d56bb72d719f11b6b291285d70825826b485811c8bb8df7db60a46` | `1ef79cfe07fc42f9fece4613dfacff40e0f51a29bc3146372dd743788da703b3` |
| `engine/legacy_harness/router_replay.py` | name cleaning | 1 |  | `58340a0eede286d853bf4735ab2ec5385fbe2916e9bfd7f2ec5709b4ca8df529` | `08caed633e74e829b8d52d4f3463badf3b14c9490bd82503f2310ac6904439b6` |
| `engine/legacy_harness/tests/test_bank_replay_tools.py` | name cleaning | 1 |  | `f599b185d9463a65bb28483d114dd1708934629ff12cf03420911b76268c123b` | `1a11eecf3188867b8f5d6660345f4c7916d4ce868755a583ba0add6ec164af9d` |
| `engine/legacy_harness/tests/test_harness_tools.py` | name cleaning | 1 |  | `9a1071c117ec1b0ea2da7feb3459acb344fd5da404a53adbb864f4f30ff633ba` | `478f7d59c22f82b7d7d305c00e5214e428de61cb9d5c22cf3317d3932cc440b9` |
| `engine/legacy_harness/tests/test_layer_replay_tools.py` | name cleaning | 1 |  | `941f2b5f7ed694805e99a690895ccb9cf4ce4ad5f60fcf50daa997cd238f0b82` | `01a5c79bf81d7c6cf0eb447c9a2d561d15eb0bb68723e8b83a3af8b360c2c767` |
| `engine/legacy_harness/tests/test_region_replay_tools.py` | name cleaning | 1 |  | `c77aa13426818491ccc9b5b99ec378ad392f57be5ded9b505bd34f56bf0c04de` | `005d8502fcaa525db275f32a324057a70f8a7b2b5f3173111cd19dbed6ee89dc` |
| `engine/OWNER_RULINGS_2026-09-28.md` | de-quote |  | 6 | `8b302907d7d7acc7b92861ace01e762f93bf728d846f32342fb263b510344b57` | `fd15287417eb84ec84594ec72ac65139f1395154390c8748911333f283e8dbfd` |
| `engine/OWNER_RULINGS_2026-10-05.md` | de-quote |  | 3 | `809ca4c747f2e314289d64e67004d83e28117bce7b0a918969ef55427cb9270b` | `9a48eb72ed84b6439d2f9a9c7e73c3a8566615459ddf652c662085e9e14e2ebc` |
| `engine/OWNER_RULINGS_2026-10-06.md` | both | 1 | 96 | `cfb8d4fe6e620e88cfc5dcc00457d27453a24373a40f1e3938ed88b5bb3445e2` | `c757a0cb8a073a4ab4fad18d16b6a5dacbe5e46b980e062a77a5271fd8faedaa` |
| `engine/PAPER_NOTES_RIVALS.md` | name cleaning | 1 |  | `061cb4a1fd1a1beede4cc16362ae7ee2f46904713a1327300c7b127f1cadd49d` | `835fcedbdca90d12ed4223b625ce56fdef9e68d5c3e1fad6a037e79a5dd4fcfd` |
| `engine/PENDING_PARTS.md` | both | 28 | 22 | `5502ad56973508a4680699b173cf1defbdd65ea1050cff2a43899dca72693e54` | `f4d9e00f3beabb144a83c718a16aa76e57dda340a93b3d65143fcf4b19dd7ed0` |
| `engine/PREREGISTRATION_DRAFT.md` | de-quote |  | 1 | `217c74369700fb621299591fa5dd350eef7a77aa8053775e2a56845517f38026` | `fbdcc07ce0caaea3899e934cb138faf04ecd812fe9fd6eb486631819a271a045` |
| `engine/PREREGISTRATION_DRAFT_coral.md` | de-quote |  | 14 | `bc070143c70a2d43962330ef6aad8e6c770dd13fc324e9b57b85ce0f309d6e2f` | `11cdbd5510f4ee6b8c3a366297827ac42278216a5ee2463db542718e2f3f4278` |
| `engine/PREREGISTRATION_DRAFT_defo.md` | de-quote |  | 1 | `8860445d253296c7b031bf4127bfbc46b78103621018e9427e918c08df2ccd45` | `6421e03d3b0ac529bcb2d0868f1e296500caf2098f4a2a71514da9c926b3940b` |
| `engine/PREREGISTRATION_DRAFT_fire.md` | de-quote |  | 1 | `daaaffe0e5a1cd327a70e90955851b5e0ff9f3c4f6f7e3a26e9cc905cf938375` | `a0196c9ac6d1bfe1458fbcbbe53d25d70a5339d6747b7b66209ea841d30296f5` |
| `engine/PREREGISTRATION_DRAFT_ndvi.md` | de-quote |  | 1 | `39f4977ca4d1ad9b95db4568922fcdefac6094397d1108c42b97d9543b8400ec` | `4181bebc66d773ea052c3c1536bdefbd0d01faca51ff37e9197bc6327e459d9d` |
| `engine/PREREGISTRATION_DRAFT_pm25.md` | de-quote |  | 1 | `e91332ab74631287eca8ff9a4b580c5109e91337e92312f14013b2bec3fa2a97` | `d27badb9e3567c7d99f7484eea23f10913e2558c475b95921f5a60267a02d3d0` |
| `engine/SMOKES_REPORT.md` | de-quote |  | 1 | `7276170a61d48ef31a4f0c24a87aa747c42e83644d620142e1c820ae53c045c1` | `39ec4f7c772161de950b78ecfa983c15c3585fc2a3c75394c2de0c89dcaac6c5` |
| `engine/speedproof/SPEEDPROOF_REPORT.md` | name cleaning | 2 |  | `cc6ecf8fb14d4255aa0696eae9d9b821149735c8c4565dd7965594359543ec85` | `f47ce402c1db296cd235a02ea12903e70e11953cd11b910f43db33e03721d36b` |
| `engine/tests/test_defo_k_ruling.py` | de-quote |  | 1 | `76aa7e223259f7322749e6eaf9c1622807cb9278d32f5d44be0150cc1ae77a99` | `f83c3e0c8260b1c6346a78638f57d0eafc80915e20a1f63258c9a1b1aafe80dc` |
| `engine/tests/test_fire_package_bans.py` | de-quote |  | 1 | `ede3fe1dc3ed472e48c5a82cba796f9efa7905f9a2b2ce4ad6e4b786b739fb51` | `5ca0b96b2f802718d1c57d97fe4fa433bab41c9ac825aa708b76b006464e6c35` |
| `engine/tests/test_ndvi_package_ban.py` | de-quote |  | 2 | `4b873783bd9fd4deaa1aa3f49f1045e5eeefc17538493ebb5d03927f0b698115` | `f97246693cc534bd8f89e81a50a91331c4397d64110ee39db8cc29209667f6bb` |
| `engine/tests/test_packages_pm25_bans.py` | de-quote |  | 1 | `73fefb4c9a91605adf33b2f9b812b1881006e7fd9f20f0224816b76e7baed570` | `668405b8879f5c2c50f653929d52468e2fc6dc91a585b09d075845bc5e9176ef` |
| `engine/tests/test_pipeline_draft.py` | de-quote |  | 1 | `d6843d8ff9751b1735bad8aa3805ef24b2687923b9f0ef95a9f676f7b9a54dab` | `b2738c46ef1f46a28f3c30c143fd4f80eafc4a6776119f2624fced55a86ba493` |
| `engine/tests/test_route_region_defo_package.py` | de-quote |  | 1 | `0d9af19b83db5a247b98dfabf2dafff6b7e51de269d39d140dd40a35d4353f03` | `7a30ae7b2bcf94447016d4715e8bf450492bc28b4106de1609a521b3531e257d` |
| `rebuild/coral_fullscale.py` | name cleaning | 1 |  | `4e4c7c9b9381891dddcc5e9005eb63ef1bf5e84446ce1c3fe4a26da6e978b70a` | `51d81ecb45948ed05fd51424bfed72a9fa5346473acfbeac8c183242a7613b06` |
| `rebuild/coral_glorys2_ab.py` | name cleaning | 1 |  | `85ee94fc1c8fc2b429e3a88a7e836646ad57888649656907fa4ab45527549720` | `4704b1905588764bee990f671cdfa48bfa614790c78ac68b05dce64d84234033` |
| `rebuild/fire_build_history.py` | name cleaning | 1 |  | `f8423e3810b2bba96eb672e17d2539e307bf169aa4ff5b6cdfe45baacd7c652c` | `19080d89ec2f942a9edf622aa9cf8f5fba6511d3b9394789319e349e490d69ea` |
| `rebuild/fire_join_drivers.py` | name cleaning | 1 |  | `f63d7ee4ca439dea2ddcb917fee1f55bbdf2150e1a778bc67c80509f51e096ee` | `cfd66acada612fc86b1e46be2511deb60417db2164ce3b0054915f3f2a4e97ab` |
| `rebuild/fire_select_cells.py` | name cleaning | 1 |  | `2b89bf4d607daba8a76447210cc1b0924843cde7bc1b0d7ae0ead567d3ccaed4` | `91f4e337ec03ffd38a702ab9ac881f2423adf5713319f0c11eaa0c25f9cd4b3e` |
| `rebuild/presplit_cc/config.yaml` | name cleaning | 5 |  | `c043ae5489971f9479d38c3a20e64c0afa784804c56a7d86db03c51e20fba8b2` | `45cdc34968225d532145c719f9e2249776180bf5d45ef4a3c3131c7314f0564d` |
| `rebuild/presplit_cc/fetch_livestock_extract.py` | name cleaning | 1 |  | `d56b0bce755d1b76b41ae344087b036ba58657673b4eede9321c80f702297ae2` | `ec2bf0ca0bea363fbd90b3af8aef2e0944b60fc4aec5a91bce3c7be933694748` |
| `records/fact_sheet/PAPER_FACTS.md` | de-quote |  | 6 | `344c581d518a851615b8a8dcfa64753ed0b957499ba1e91268feb8dc2063002a` | `d3f6cc53c73728eeeed3df919eadba7c07f2d0b4b56a26aa38a5ccf8d52f15a7` |
| `records/paper_checks/models_scan.txt` | name cleaning | 4 |  | `3720450824e80d2909c8fb1c4538b8ea4164ff1adead6acb5149d25f3746cbff` | `7848f0f88c9172a372931984ccdcc8aaccf0bca1c8d7d9fba35c58c3c57535fa` |
| `records/paper_checks/py_writes.csv` | name cleaning | 4448 |  | `74b3b9f69ab8333dc0ad5fe8d4bbbeb52581c7d31574e1ed4d8d5f2f5afd2053` | `a38c0282293a6ec1502184fdec98fa97fc35ef6a143cdce25aecda6cdf7f1c73` |
| `records/project_docs/APP_PLAN.md` | de-quote |  | 3 | `ebe331ba1745d75808bb978fdaa7cb040e96bf4958262c018a6bad54503fafa9` | `32a52c9bf7a5201e5f10ccb92454073cacbe41a2a513d96ec1b770fa2ce967fe` |
| `records/project_docs/HEADLINE_QUESTIONS_AND_FIXES.md` | de-quote |  | 2 | `c7848ecee36a8f64bce626c0bd94c13c6d0ab6eab4f4e63bfb2e1e3f78f14717` | `b18eaa6547a2ba00fec57218bdf33ef4d3a9b37d910107b9a6e312646dfdd7e8` |
| `records/project_docs/QUESTIONS_ROUND3_HANDOFF.md` | de-quote |  | 1 | `ee17680466a6393eb9074384dee0a176c6038e3e281ba6c196d9288f5c99cdfa` | `32643dd7fd7026ffea6b104f9e5b93baf470f87311a353c70dea753fc27c63f0` |
| `rivals_code/human_rivals_build/human/human_rivals.yaml` | name cleaning | 2 |  | `69ee7eca0b055c0adfd3ba638d0dad8fa65ff87f19be012a7f7e03b7809bbe20` | `2f31f395acac1e028a8da46a748536e106a27c6041f25ef30eb89bebebbdde82` |
| `rivals_code/human_rivals_build/human/human_rivals_DRY.DRAFT.yaml` | name cleaning | 2 |  | `bfc3ceef3008acc9dab65ff44d514aa6ceeb899d0b5d28b71bcc988430c39015` | `728b8546fecc9d7ec0039726d30ada27b6cd25c2aa91b71ebe9d350972675ec8` |
| `rivals_code/human_rivals_build/human/human_rivals_production.DRAFT.yaml` | name cleaning | 2 |  | `76aa539f0726f2b5985a9daeffdb393f6ad2e6d6a78f70e7a7582a0c99639ef2` | `8aa54d03580989403ac4e09b255377f4a248dd31bbf5050cf4e16ce310e25a3c` |
| `rivals_code/human_rivals_build/human/rivals_human/tests/conftest.py` | name cleaning | 1 |  | `ac46ec26994d24b20b1689e02f98945ca59c58c60879c2a7c8da41be16a891ad` | `a337a2caae92d861a56176b54b9250b0a28dddb998a2970e8b583b7f922614ec` |
| `rivals_code/human_rivals_build/human/rivals_human/tests/hooks.py` | name cleaning | 1 |  | `1bdf16f0550044aa6b2c9c2caaec06b821c4f945d2d7c95a1eda1f9852a4b9c9` | `749e1d3b1b050b5c3c62eccd80668d97753c595add24cfc150ffc07d821f8987` |
| `rivals_code/human_rivals_build/human/tests_fire/conftest.py` | name cleaning | 1 |  | `dd6629a4d8729421a9a3697fde1ccc6402465558bc508c700ef268f25151f1b2` | `60c7ed2ea5e4cc50491d3b43b7629369dc106d9d0e9352996a7b1dc55152285f` |
| `rivals_code/human_rivals_build/human/tests_fire/fixtures_fire.py` | name cleaning | 1 |  | `afc375059e6877ecd12f3da4e86a9421b6103a1ea8287e2112374a8e54aa6dfd` | `c067605a9ea23acf170502c4cc7a7c3dc634a2a15f854436bd019f3ea178a06d` |
| `rivals_code/human_rivals_build/pt/tests/final_full_20261025T2057Z.log` | name cleaning | 5 |  | `1cdd0a7baa1dc10f9bf09eda99f9cf75b4e18ef7569dfecb034497fa58ac25ab` | `beaaad4fdbdfde1f011c7dd8ec94b58ab4615f87b935120fbc6a4c8715d7b2bb` |
| `rivals_code/human_rivals_build/pt/tests/final_review_20261025T2105Z.log` | name cleaning | 4 |  | `99041bfaae1944d9bf96c11c40355b7b255a8f9d46ab0e1aefec3afc59d0decb` | `a8c66175e6388f1afca4af327eacdac8a9a897dec36dce1287c042e52d781923` |
| `rivals_code/human_rivals_build/SPEC_HUMAN.txt` | name cleaning | 1 |  | `a7ca044348b170c4ddd616e5c056e2d1cca0c5e31e954c98b6ddbecf087d5e32` | `79abdd10c480e27f57a10b74d512dac560a782fe46cde80c0f1e8fc01a19185a` |
| `rivals_code/human_rivals_build/SPEC_HUMAN_PARTB.txt` | name cleaning | 3 |  | `f2c476b0429fc2bd2c876bc4d600228f3b0b3cd1df2bb8da77e72f90cdc756a2` | `fb2a7f63673332d8968a66f8c1fe4d176bfe9cb3cef7fdcb81321ea1219b761b` |
| `rivals_code/human_tools/DOWNLOAD_COMMANDS.md` | name cleaning | 3 |  | `cdd2617521049cdf886dc2549c5f7305b0d1c2da5b152a639c4b0915000c8915` | `9740f583b244f9131364bb8ec0ee2c078dad398ec69359097bc76a4323715c99` |
| `rivals_code/human_tools/dryrun_keyed.txt` | name cleaning | 4 |  | `0c1e591f740e499ca8e87a9b5049103e7cf67f1fa108f5624ae3c402015db244` | `80965b19828cf7113f9821e8d9c49fe2ae9ea80b2d5ab30375560d73e3ea78e5` |
| `rivals_code/human_tools/dryrun_keyed_region_boxes.txt` | name cleaning | 2 |  | `8cd0fcaf0f36b65f2dad6c4a7c5d57537e09e433fb962d165364501a1786283d` | `2cd36352dec6b61b6321bda88663dba07bb3772e5adedabf4bb39079508ce4fa` |
| `rivals_code/human_tools/fetch_products.py` | de-quote |  | 1 | `5f5249087c5cbcba68ba2dc33cbd5c60b2250d6eb86d41101d15393db93c30fc` | `e52f431e5366b27e86a0faa26211ea0c2f68d114f07581addfb72346667a0e48` |
| `rivals_code/rivals_build/evidence/z1/constants_diff.py` | name cleaning | 1 |  | `85ede5fb962fb08c9d915b4a4661a1add1cc48f9264d88f899615f2d65d84430` | `08b4dc87a52aec8797c1b7988ce1cd8778c183c0acea0181910d5f733b48f053` |
| `rivals_code/rivals_build/finish_ndvi_smoke.ps1` | name cleaning | 1 |  | `bad98b9008ce2eb0ef0490803a4240e6213e3f99d341e0c5e9983ae803b20f7d` | `e2e29ffdb45aac6bfe1260e2490f0eff9afec9449881d7ab9544a9f4008580b2` |
| `rivals_code/rivals_build/follow_defo.ps1` | name cleaning | 1 |  | `3ec1b244e3ab4416707a43b04e92c21bb0512016164514bad1d7a054c407b130` | `3c39a20ed9d93c2e6e97ad1ead4f4e0a31b148401ef7c94a14779a6861306b04` |
| `rivals_code/rivals_build/follow_kraft.ps1` | de-quote |  | 1 | `d663f72d82169e26a7baba30de46820ebacb3ef8e65baec86d974605a1677c3a` | `84acfa673fc58c9f10c9f0054a92ba677dd1eb741330b865293b90dd4b564ffe` |
| `rivals_code/rivals_build/follow_ndvi.ps1` | name cleaning | 1 |  | `eb390cae9f57c0384f8b2c52a8127106740b1bc55f4ccdd5e1af442273964b54` | `ba443a3f509e6be43aa472f4a4857741f4ff5dd114bc22db148906d0777d6496` |
| `rivals_code/rivals_build/follow_pm25_then_ndvi_smoke.ps1` | name cleaning | 1 |  | `6ac0405f3d9acc7a8744b06038514ff6393bed068e37db837b09e2e30d5d4e26` | `428268a08bac3506846dd278d215cabe91d45d050906d83a466a1821f0f1da6b` |
| `rivals_code/rivals_build/rivals.yaml` | name cleaning | 1 |  | `0da7ee8883438479c29ac7b9cc4049470017955adaf4b0d3050be892a60b5e29` | `4e9b1797525cd3c67208a6b1bd87be271d6da66f0b422d34db35776be91e59c7` |
| `rivals_code/rivals_build/rivals/tests/conftest.py` | name cleaning | 1 |  | `d5b875e8ba82cf2816e5b19e964553b3463101a9ae6a86f318d9624dcd06d342` | `c909b6da58fb238a822b8c94477154d583a6ca5df10693d724dd872d7de890ad` |
| `rivals_code/rivals_build/rivals/tests/test_aa_speedups.py` | de-quote |  | 2 | `1417168a1174ee5fc48064cafdbc63d98b3385629243d92ea9cb6c6fe7318a0c` | `f68426c24810023c0069544057574f299b08aeb1893c56ecb64e342da44d47a7` |
| `rivals_code/rivals_build/rivals/tests/toy_runs.py` | name cleaning | 1 |  | `93810159bd89ecad97f11296d44b33fbb1c665926136fc4e7a8a26b95850a0ac` | `1cd21f8ea0df4985a2790ac619b821ab8360a2b2153a6319d1d2c7ac9f734da4` |
| `rivals_code/rivals_build/RIVALS_OWNER_COMMANDS.md` | name cleaning | 1 |  | `76537dff0ea2d9abe269aee502b427cf740195c8ba7dfb2a08624fdff909388d` | `57e1785ae0ea913829ab5d7206c685da79eb0b5e2e35cc53998b7572fcc79322` |
| `rivals_code/rivals_build/rivals_production.yaml` | name cleaning | 2 |  | `8ac3a1aab555229db276194a350a9c9b0857fd31c51d437275fa91b4a1068670` | `59231b9ab278e2b241f17db73857d2646cc5dc976fa300ae8a2efe8f3bc5852d` |
| `rivals_code/rivals_build/SPEC_RIVALS.md` | both | 2 | 3 | `3faa25af0ac304492801831158c5dda1cd022f81a6ac78e003648a637e50f406` | `e15b29510c59b4800f49eef937992cfcda198c309aee4acc464ae18e46eec028` |
| `rivals_code/rivals_plan_human/protocol.md` | name cleaning | 1 |  | `087d69bac78bb4952e5c5c95ce7570da10224566d6b77ccf0c04f07a70b7b4d7` | `c91ef75c9e8e26441b12265ee3b4d897c8d309bbad7dd31620208a683a75f2fa` |
| `rivals_code/rivals_plan_human/research_coral.md` | name cleaning | 1 |  | `d8da294acfaf98c7f6bf13427ff380c9379deefc6cbe45ff5f9dc8ce7246398d` | `a256eb341d174a3bc4db16d52e8e253ba71da9cac546ff91700f5ab563e8d897` |
| `rivals_code/rivals_plan_human/research_pm25.md` | name cleaning | 2 |  | `790675a80ec0ec3a6b65d31a96afa5eaced26dc8e8398937c64f946a4c9c4cf1` | `a67a05309166fa998bf2892a60e6776800511d2a734ea0cf36eef8826dfc91ab` |
| `versions/engine/_moved_coral_20261020_014111/INSTALL_MANIFEST.json` | name cleaning | 16 |  | `9faf6519311fd6dac423ec723fbb6f4e5bb7284054036e8ec26d713260adc7d7` | `53be458c786619a36b61e0bfefcd78d53c943951cd9c50b5fc38d3af16957fd0` |
| `versions/engine/_moved_coral_20261020_064437/INSTALL_MANIFEST.json` | name cleaning | 9 |  | `6e9ca2243b5f4a44bda9321280ae5833b122c6dba4c9d75534ddeb716f5b0b29` | `5484cb0cb84ea369a702f8f81275384350844b4d00c65d942419d7b6576bc21b` |
| `versions/engine_v2/_moved/pre_skeptic_fixes_20261021/legacy_harness/layer_replay.py` | name cleaning | 1 |  | `846ed6b10ab9368f23460c2e4f6cb89ea9de9640016ffec45f9068d871ef3daa` | `58f3449178da2d38f1af0cc9da95b5c7856a84e8f851fd4e3d71f73657af89de` |
| `versions/engine_v2/engine/legacy_harness/bank_replay.py` | name cleaning | 1 |  | `f29478fd8409336cd69a55dd6a2a0757f8f8f56549013c2fb4dcb83959e49c0f` | `517f2ccdfb4c885b6bdb5fb0e1f36efa1040f3800e41b6f7b82d43c984abc903` |
| `versions/engine_v2/engine/legacy_harness/datasets/defo_draft/dataset.yaml` | de-quote |  | 1 | `1c1ecd9e413faf4210db94a7be5e010744e2904ba2817ded91469636d28eb542` | `40519d10a3093bc486e62fb736e5f6d8a487c1186a93944bdd1445e0fe855982` |
| `versions/engine_v2/engine/legacy_harness/goldens_v3.json` | name cleaning | 18 |  | `de311490f1bfafa3f1aa0fa1dc71c90d7a9f0d27d871263431efc3c1a1a1ce16` | `4f2eaa095a10bfe1baf91e3b8a2e1f8c9c86f0c362d0f6d2e99f52d4e3773e1a` |
| `versions/engine_v2/engine/legacy_harness/layer_replay.py` | name cleaning | 1 |  | `846ed6b10ab9368f23460c2e4f6cb89ea9de9640016ffec45f9068d871ef3daa` | `58f3449178da2d38f1af0cc9da95b5c7856a84e8f851fd4e3d71f73657af89de` |
| `versions/engine_v2/engine/legacy_harness/README.md` | name cleaning | 2 |  | `626e3944db398b982ffd93db8207ddc08798153860f94c73523d15876747db30` | `0edb2fe94582ec6bc2219c2a03a70a8b005a04de610e94c4d08face5c83b57c4` |
| `versions/engine_v2/engine/legacy_harness/region_replay.py` | name cleaning | 1 |  | `d4c37a9693d56bb72d719f11b6b291285d70825826b485811c8bb8df7db60a46` | `1ef79cfe07fc42f9fece4613dfacff40e0f51a29bc3146372dd743788da703b3` |
| `versions/engine_v2/engine/legacy_harness/router_replay.py` | name cleaning | 1 |  | `58340a0eede286d853bf4735ab2ec5385fbe2916e9bfd7f2ec5709b4ca8df529` | `08caed633e74e829b8d52d4f3463badf3b14c9490bd82503f2310ac6904439b6` |
| `versions/engine_v2/engine/legacy_harness/tests/test_bank_replay_tools.py` | name cleaning | 1 |  | `f599b185d9463a65bb28483d114dd1708934629ff12cf03420911b76268c123b` | `1a11eecf3188867b8f5d6660345f4c7916d4ce868755a583ba0add6ec164af9d` |
| `versions/engine_v2/engine/legacy_harness/tests/test_harness_tools.py` | name cleaning | 1 |  | `9a1071c117ec1b0ea2da7feb3459acb344fd5da404a53adbb864f4f30ff633ba` | `478f7d59c22f82b7d7d305c00e5214e428de61cb9d5c22cf3317d3932cc440b9` |
| `versions/engine_v2/engine/legacy_harness/tests/test_layer_replay_tools.py` | name cleaning | 1 |  | `941f2b5f7ed694805e99a690895ccb9cf4ce4ad5f60fcf50daa997cd238f0b82` | `01a5c79bf81d7c6cf0eb447c9a2d561d15eb0bb68723e8b83a3af8b360c2c767` |
| `versions/engine_v2/engine/legacy_harness/tests/test_region_replay_tools.py` | name cleaning | 1 |  | `c77aa13426818491ccc9b5b99ec378ad392f57be5ded9b505bd34f56bf0c04de` | `005d8502fcaa525db275f32a324057a70f8a7b2b5f3173111cd19dbed6ee89dc` |
| `versions/engine_v2/engine/tests/test_defo_k_ruling.py` | de-quote |  | 1 | `76aa7e223259f7322749e6eaf9c1622807cb9278d32f5d44be0150cc1ae77a99` | `f83c3e0c8260b1c6346a78638f57d0eafc80915e20a1f63258c9a1b1aafe80dc` |
| `versions/engine_v2/engine/tests/test_fire_package_bans.py` | de-quote |  | 1 | `ede3fe1dc3ed472e48c5a82cba796f9efa7905f9a2b2ce4ad6e4b786b739fb51` | `5ca0b96b2f802718d1c57d97fe4fa433bab41c9ac825aa708b76b006464e6c35` |
| `versions/engine_v2/engine/tests/test_ndvi_package_ban.py` | de-quote |  | 2 | `4b873783bd9fd4deaa1aa3f49f1045e5eeefc17538493ebb5d03927f0b698115` | `f97246693cc534bd8f89e81a50a91331c4397d64110ee39db8cc29209667f6bb` |
| `versions/engine_v2/engine/tests/test_packages_pm25_bans.py` | de-quote |  | 1 | `73fefb4c9a91605adf33b2f9b812b1881006e7fd9f20f0224816b76e7baed570` | `668405b8879f5c2c50f653929d52468e2fc6dc91a585b09d075845bc5e9176ef` |
| `versions/engine_v2/engine/tests/test_pipeline_draft.py` | de-quote |  | 1 | `d6843d8ff9751b1735bad8aa3805ef24b2687923b9f0ef95a9f676f7b9a54dab` | `b2738c46ef1f46a28f3c30c143fd4f80eafc4a6776119f2624fced55a86ba493` |
| `versions/engine_v2/engine/tests/test_route_region_defo_package.py` | de-quote |  | 1 | `0d9af19b83db5a247b98dfabf2dafff6b7e51de269d39d140dd40a35d4353f03` | `7a30ae7b2bcf94447016d4715e8bf450492bc28b4106de1609a521b3531e257d` |
| `versions/human_rivals_build/_moved/20261022_review_fixes_before/SPEC_HUMAN.txt` | name cleaning | 1 |  | `f765d4358017703aa46674695e78817d2d6c2e63e506ad44717f3f9eabcbf09a` | `13e3fc38e0a737a6b9f1e137140e601b0a7a2123a91b173a9ce67834587055bf` |
| `versions/human_rivals_build/_moved/PREREGISTRATION_DRAFT_human_partA.before_shas_20261025.txt` | de-quote |  | 2 | `8e21627ca2d68b4e3935429d3b4ac02670c9de02968532d16b782b6149b2d535` | `107951f86888029a9d08d25bb5d6dc090cd43d09a147a96f3fb54511fd314f51` |
