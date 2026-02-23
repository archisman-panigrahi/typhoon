# Makefile for Typhoon COPR builds

SPECFILE = fedora-package.spec
VERSION = $(shell grep "^Version:" $(SPECFILE) | awk '{print $$2}')
NAME = $(shell grep "^Name:" $(SPECFILE) | awk '{print $$2}')

.PHONY: help srpm clean

help:
	@echo "Typhoon COPR Build Helper"
	@echo ""
	@echo "Available targets:"
	@echo "  srpm   - Generate source RPM for COPR"
	@echo "  clean  - Clean generated files"
	@echo "  help   - Show this help message"
	@echo ""
	@echo "Current version: $(VERSION)"

srpm:
	@echo "Building source RPM for $(NAME) v$(VERSION)..."
	@mkdir -p ~/rpmbuild/SOURCES ~/rpmbuild/SPECS
	@spectool -g -R $(SPECFILE)
	@rpmbuild -bs $(SPECFILE)
	@echo ""
	@echo "Source RPM created successfully!"
	@echo "Location: ~/rpmbuild/SRPMS/$(NAME)-$(VERSION)-1.*.src.rpm"
	@echo ""
	@echo "To upload to COPR:"
	@echo "  copr-cli build <your-project> ~/rpmbuild/SRPMS/$(NAME)-$(VERSION)-1.*.src.rpm"

clean:
	@rm -rf ~/rpmbuild/BUILD/$(NAME)-$(VERSION)
	@echo "Cleaned build artifacts"
