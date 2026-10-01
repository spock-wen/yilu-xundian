package ohos_app_cangjie_entry

public func rawImg(name: String): String {
    return "resource://RAWFILE/" + name + ".png"
}

public func rawSvg(name: String): String {
    return "resource://RAWFILE/" + name + ".svg"
}

/* 单向门「乙·闸门栅」idle 切片(oneway-gate-B-locked/assets/oneway-B-idle-{0,90}@48.png 原样拷贝)。
   两个字面量分开写,sync_to_keels.sh 的 rawImg("...") 正则需要字面量。 */
public func gateImgSrc(vertical: Bool): String {
    if (vertical) {
        return rawImg("oneway_b_idle_v")
    }
    return rawImg("oneway_b_idle_h")
}

/* 单向门「乙·闸门栅」reject 切片(官方锁定包 oneway-B-reject-{0,90}@48.png 原样拷贝,sha256 已核对;
   与 idle 同画布)。两个字面量分开写,sync_to_keels.sh 的 rawImg("...") 正则需要字面量。 */
public func gateRejectImgSrc(vertical: Bool): String {
    if (vertical) {
        return rawImg("oneway_b_reject_v")
    }
    return rawImg("oneway_b_reject_h")
}
