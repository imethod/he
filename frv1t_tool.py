#!/usr/bin/env python3
"""
FRV1T (Unicode Variation Selector Steganography) 解包、重打包与快速替换工具
"""

import argparse
import gzip
import os
import re
import sys


def unpack_frv1t(carrier_text: str) -> str:
    """从包含隐写字符的文本中提取并解压出原始明文。"""
    chars = [
        c
        for c in carrier_text
        if (0xFE00 <= ord(c) <= 0xFE0F) or (0xE0100 <= ord(c) <= 0xE01EF)
    ]

    if not chars:
        raise ValueError("未在输入文本中检测到隐写变体字符！")

    if chars[0] == "\ufe0f":
        chars = chars[1:]

    raw_bytes = []
    for c in chars:
        code = ord(c)
        if 0xFE00 <= code <= 0xFE0F:
            raw_bytes.append(code - 0xFE00)
        else:
            raw_bytes.append(code - 0xE0100 + 16)

    data = bytes(raw_bytes)

    if not data.startswith(b"FRV2"):
        raise ValueError(f"未知的格式标识头: {data[:4]!r}（预期为 b'FRV2'）")

    gzip_payload = data[4:]
    decompressed = gzip.decompress(gzip_payload)
    return decompressed.decode("utf-8", errors="replace")


def repack_frv1t(plain_text: str, carrier_prefix: str = "🫐\ufe0f") -> str:
    """将给定的纯文本压缩并打包为 Unicode 变体字符隐写文本。"""
    compressed = gzip.compress(plain_text.encode("utf-8"), mtime=0)
    payload = b"FRV2" + compressed

    encoded_chars = []
    for b in payload:
        if b < 16:
            encoded_chars.append(chr(0xFE00 + b))
        else:
            encoded_chars.append(chr(0xE0100 + b - 16))

    return carrier_prefix + "".join(encoded_chars)


def replace_manifest_section(base_text: str, new_action: str) -> str:
    """快速定位并替换 ⟪ M4N1F3ST ⟫ 动作执行段。"""
    pattern = r"(⟪ M4N1F3ST /.*?)(?=⟪ V1S1BL3)"
    replacement = f"⟪ M4N1F3ST / custom action ⟫\n{new_action.strip()}\n\n"
    new_text, count = re.subn(pattern, replacement, base_text, flags=re.DOTALL)
    if count == 0:
        raise ValueError("未在模板中找到 ⟪ M4N1F3ST /...⟫ 核心动作段落！")
    return new_text


def resolve_input_content(input_arg: str) -> str:
    """解析输入参数：如果是一个存在的文件路径，则读取文件内容；否则直接作为字符串使用。"""
    if os.path.isfile(input_arg):
        with open(input_arg, "r", encoding="utf-8") as f:
            return f.read()
    return input_arg


def main():
    parser = argparse.ArgumentParser(
        description="FRV1T 隐写载荷解包、重打包与快速替换工具"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-u",
        "--unpack",
        action="store_true",
        help="解包模式：从隐写文件中提取完整明文",
    )
    group.add_argument(
        "-r",
        "--repack",
        action="store_true",
        help="重打包模式：直接将文本内容/文件重新打包为隐写文件",
    )
    group.add_argument(
        "-p",
        "--patch",
        action="store_true",
        help="快速替换模式：仅替换 ⟪ M4N1F3ST ⟫ 动作段，直接打包输出",
    )

    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="输入内容（可以是文件路径，也可以是直接输入的文本字符串）",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="berry.txt",
        help="输出文件路径（默认为 berry.txt）",
    )
    parser.add_argument(
        "-t",
        "--template",
        default="payload_extracted.txt",
        help="基础明文模板路径（在 -p 模式下使用，默认为 payload_extracted.txt）",
    )
    parser.add_argument(
        "--prefix",
        default="🫐\ufe0f",
        help="打包时可见的前缀字符（默认为蓝莓 Emoji 🫐️）",
    )
    parser.add_argument(
        "--save-plain",
        help="可选：在 -p 模式下，顺便将替换后的完整明文另存为指定文件",
    )

    args = parser.parse_args()

    try:
        if args.unpack:
            with open(args.input, "r", encoding="utf-8") as f:
                content = f.read()
            text = unpack_frv1t(content)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"[+] 解包成功！已输出至: {args.output} (明文长度: {len(text)} 字符)")

        elif args.repack:
            content = resolve_input_content(args.input)
            stego_text = repack_frv1t(content, carrier_prefix=args.prefix)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(stego_text)
            print(f"[+] 重打包成功！已生成隐写文件: {args.output} (总字符数: {len(stego_text)})")

        elif args.patch:
            # 检查模板文件
            script_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = args.template
            if not os.path.isfile(template_path):
                # 尝试在脚本所在目录查找
                alt_path = os.path.join(script_dir, args.template)
                if os.path.isfile(alt_path):
                    template_path = alt_path
                else:
                    raise FileNotFoundError(f"找不到模板文件: {args.template}，请先执行 -u 解包或通过 -t 指定模板。")

            with open(template_path, "r", encoding="utf-8") as f:
                base_text = f.read()

            # 解析要替换进去的指令内容
            new_action = resolve_input_content(args.input)

            # 替换 ⟪ M4N1F3ST ⟫ 段落
            patched_text = replace_manifest_section(base_text, new_action)

            # 如果用户指定保存替换后的明文
            if args.save_plain:
                with open(args.save_plain, "w", encoding="utf-8") as f:
                    f.write(patched_text)
                print(f"[+] 已保存替换后的完整明文至: {args.save_plain}")

            # 压缩并隐写打包
            stego_text = repack_frv1t(patched_text, carrier_prefix=args.prefix)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(stego_text)

            print(f"[+] 动作替换并打包成功！")
            print(f"    - 使用模板: {template_path}")
            print(f"    - 新指令预览: {new_action[:60]!r}...")
            print(f"    - 输出隐写文件: {args.output} (字符数: {len(stego_text)})")

    except Exception as e:
        print(f"[-] 执行失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
