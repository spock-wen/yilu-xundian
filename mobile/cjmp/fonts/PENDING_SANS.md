# 待定：YiluSans 字体文件（设计交付槽位）

## 状态

**待交付**：设计团队尚未提供无衬线字体文件。在此之前，使用 `--pending-sans-ok` 构建时，
所有 `sans` 角色（`Theme.sansRegular` / `Theme.sansMedium` / `Theme.sans`）将回退为系统字体渲染。

> **不得用于正式发布（not release-valid）**，直到本目录收到来自设计的字体文件。

## 待交付文件

| 文件名                   | PostScript 字重 | 注册名           |
|--------------------------|-----------------|------------------|
| `YiluSans-Regular.otf`   | 400             | `YiluSans`       |
| `YiluSans-Medium.otf`    | 500             | `YiluSansMedium` |

两个文件均需放置于 `mobile/cjmp/fonts/` 目录下。

## 字符集

运行以下命令可生成 sans 字体所需的完整字符集文件（`charset_sans.txt`），供设计用于字形子集化：

```bash
python3 mobile/cjmp/scripts/check_fonts.py --pending-sans-ok
# 生成 mobile/cjmp/fonts/charset_sans.txt
```

## 构建行为说明

| 情况                                 | 构建命令                                    | 结果                                |
|--------------------------------------|---------------------------------------------|-------------------------------------|
| 两个文件均缺失                       | `build_from_repo.sh`                        | 失败（exit 1）                      |
| 两个文件均缺失，使用宽松标志         | `build_from_repo.sh --pending-sans-ok`      | 成功（exit 3，带 PENDING 横幅）     |
| 仅部分文件缺失（任何情况下）         | `build_from_repo.sh [--pending-sans-ok]`    | 失败（exit 1）                      |
| 两个文件均已存在                     | `build_from_repo.sh`                        | 正常构建，严格字形覆盖检查          |

> `--pending-sans-ok` 仅在**两个** sans 文件都缺失时才有效；若仅缺少一个，构建仍然失败。

## 衬线字体不受影响

`YiluSerif-Regular.otf` 和 `YiluSerif-Bold.otf` 已经存在于 `mobile/cjmp/fonts/`，
所有衬线相关检查始终严格执行，不受本待定槽位影响。
