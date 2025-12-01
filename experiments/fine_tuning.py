import logging
import sys
import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model
from trl import SFTTrainer

class UkrT5:
    def __init__(self, model_id="t5-large"):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initializing UkrT5 with model_id=%s", model_id)
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)

        try:
            use_bf16 = torch.cuda.is_bf16_supported()
        except Exception:
            use_bf16 = False

        compute_dtype = torch.bfloat16 if use_bf16 else torch.float16

        self.bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
        )

        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            model_id,
            quantization_config=self.bnb_config,
            device_map="auto"
        )

        self.model.gradient_checkpointing_enable()
        self.model = prepare_model_for_kbit_training(self.model)

    def __setup_lora(self):
        self.logger.debug("Setting up LoRA adapters")
        lora_config = LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=["q", "v", "k", "o", "wi", "wo", "lm_head"],
            bias="none",
            lora_dropout=0.05,
            task_type="SEQ_2_SEQ_LM",
        )
        self.model = get_peft_model(self.model, lora_config)

    def lora_train(self, dataset_path):
        self.logger.info("Starting LoRA training. dataset_path=%s", dataset_path)
        self.__setup_lora()
        dataset = self.format_dataset(dataset_path)
        self.logger.info("Dataset size: %d", len(dataset))

        bf16_arg = False
        fp16_arg = False
        try:
            bf16_arg = torch.cuda.is_bf16_supported()
        except Exception:
            bf16_arg = False
        fp16_arg = torch.cuda.is_available() and not bf16_arg

        training_args = TrainingArguments(
            output_dir="t5_lora_output",
            num_train_epochs=1,
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,
            learning_rate=1e-4,
            warmup_ratio=0.05,
            logging_steps=10,
            save_strategy="epoch",
            fp16=fp16_arg,
            bf16=bf16_arg,
            optim="paged_adamw_32bit"
        )
        self.logger.debug("Training arguments: %s", training_args.to_dict() if hasattr(training_args, 'to_dict') else str(training_args))
        self.trainer = SFTTrainer(
            model=self.model,
            train_dataset=dataset,
            args=training_args
        )

        self.logger.info("Beginning trainer.train()")
        try:
            train_result = self.trainer.train()
            self.logger.info("Training finished. result=%s", getattr(train_result, 'metrics', train_result))
        except Exception as e:
            self.logger.exception("Exception during training: %s", e)
            raise

    def fuse_lora(self):
        self.logger.info("Fusing LoRA adapters into base model")
        adapter_model = self.trainer.model
        merged_model = adapter_model.merge_and_unload()
        self.model = merged_model
        self.tokenizer = self.trainer.tokenizer
        self.logger.info("Fusing complete")

    @staticmethod
    def format_prompts(example, tokenizer=None):
        category = example.get("category", "")
        info = example.get("info", "")
        resume = example.get("resume", "")

        input_text = f"Generate resume for category: {category}\nInfo: {info}"
        target_text = resume
        return {"input_text": input_text, "target_text": target_text}

    def format_dataset(self, csv_path):
        self.logger.info("Loading dataset from %s", csv_path)
        dataset = load_dataset("json", data_files=csv_path, split="train")

        self.logger.debug("Mapping prompts to dataset")
        dataset = dataset.map(lambda x: self.format_prompts(x, self.tokenizer))

        def tokenize_function(batch):
            tokenized = self.tokenizer(
                batch["input_text"],
                text_target=batch["target_text"],
                padding="max_length",
                truncation=True,
                max_length=512,
            )
            tokenized["labels"] = [
                [(l if l != self.tokenizer.pad_token_id else -100) for l in labels]
                for labels in tokenized["labels"]
            ]
            return tokenized
        self.logger.debug("Tokenizing dataset (batched)")
        dataset = dataset.map(tokenize_function, batched=True)

        remove_cols = ["input_text", "target_text", "category", "info", "resume"]
        dataset = dataset.remove_columns([c for c in remove_cols if c in dataset.column_names])
        self.logger.info("Finished formatting dataset. columns now: %s", dataset.column_names)

        return dataset

def setup_logging(level=logging.INFO):
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(stream=sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(level)


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    try:
        logger.info("Script started")
        ukr_t5 = UkrT5()
        ukr_t5.lora_train("cv_augmented_dataset.jsonl")
        ukr_t5.fuse_lora()

        logger.info("Saving final model and tokenizer to 'ukr_t5_resume_model'")
        ukr_t5.model.save_pretrained("ukr_t5_resume_model")
        ukr_t5.tokenizer.save_pretrained("ukr_t5_resume_model")
        logger.info("Script finished successfully")
    except Exception as exc:
        logger.exception("Fatal error in main: %s", exc)
        raise
